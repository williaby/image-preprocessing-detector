# Training Data Strategic Analysis: Go/No-Go Assessment

> **Document**: Training Data Strategic Analysis
> **Version**: 1.0.0
> **Date**: 2026-02-24
> **Status**: COMPLETE
> **Sources**: HAR_SYNTHESIS.md, CORPUS_OOD_REVIEW_REPORT.md, OOD_COVERAGE_GAP_REPORT.md, 22-head scoring matrix, 4 consensus rounds (Gemini 2.5 Pro, Gemini 3 Pro Preview, DeepSeek R1 0528, Grok 4)
> **Scope**: 22 training heads across MobileNetV4-Conv-S (3 heads) and SigLIP 2 NAFlex (19 heads)

---

## Executive Summary

### Verdict: CONDITIONAL GO

Proceed with T4+T6 data tier (Enriched Current + Computational Enhancements), descoped to 16 heads for Release 1. Defer 6 heads (G4 handwriting group of 5 + G3-2 narrow-range skew) to Release 2 pending T5 targeted data acquisition.

**Mean confidence across 4 AI models: 8.5/10** (Gemini 2.5 Pro 9/10, Gemini 3 Pro Preview 9/10, DeepSeek R1 0528 8/10, Grok 4 8/10).

### Current State

| Metric | Value |
|--------|-------|
| Total heads | 22 |
| Mean readiness score | 27/100 |
| Heads blocked (score < 30) | 8 |
| Heads needs-work (score 30-59) | 14 |
| Heads near-ready (score 60-74) | 0 |
| Heads ready (score >= 75) | 0 |
| Immediately trainable | 2 (MNV4-H1 orientation, MNV4-H2 skew) |
| Architectural defects on critical path | 3 (must-fix before any training) |

### Target State at T4+T6

| Metric | Value |
|--------|-------|
| Heads blocked | 0 |
| Heads needs-work | 9 |
| Heads near-ready | 7 |
| Heads ready | 6 (G1-1, G1-2, G1-3, G1-5, G1-6, G5-2) |
| Performance ceiling | approximately 75% of ideal |
| Trainable head count | All 22 unblocked; 16 at quality gate for Release 1 |

### Three Must-Fix Architectural Defects

These defects are on the critical path and must be resolved before any training labels are generated. Total effort: 3-5 hours.

1. **N_A Sentinel Value (CRITICAL)**: Handwriting presence/legibility heads encode "no handwriting" as 0.0, which is semantically identical to "fully absent/illegible." Fix: change to -1.0 with masked loss. Affects 5 heads (SIG-G4-1 through G4-5).
2. **code_reg Misclassified as Regression (HIGH)**: Binary classification task configured with MSE loss. Fix: rename to code_cls, switch to BCE loss. Affects SIG-G5-4.
3. **SIG-G3-2 Skew Derivation Conflict (MEDIUM)**: Unsigned vs. signed regression target ambiguity. Fix: explicit design decision + implementation alignment. Affects SIG-G3-2.

### Go/No-Go Decision Matrix

| Horizon | MNV4 (3 heads) | SigLIP Core (11 heads) | SigLIP Expanded (16 heads) | G4 Handwriting (5 heads) |
|---------|-----------------|------------------------|----------------------------|--------------------------|
| 4 weeks | CONDITIONAL GO | NO-GO | NO-GO | NO-GO |
| 8 weeks | GO | CONDITIONAL GO | NO-GO | NO-GO |
| 12 weeks | GO | GO | CONDITIONAL GO | NO-GO (Release 2) |
| 16+ weeks | GO | GO | GO | CONDITIONAL GO (T5 data) |

**Conditional GO criteria:**

- 4-week MNV4: All 3 defects fixed + legal deployment model decided
- 8-week SigLIP Core: E11 (v3 completion) + E01 (shadow labeling) complete + legal clear + 7 or more heads at val SRCC > 0.65
- 12-week Expanded: E03 (warping) + E05 (resolution quality V2) complete + G3 heads integrated + 14 or more heads at quality gate
- 16-week G4: T5 handwriting data acquired (KHATT, CASIA, IIIT) + ILLEGIBLE class synthesized

### Unanimous Findings Across All 4 Consensus Rounds

1. **T2 and T3 tiers are dominated dead ends.** License-only tiers produce zero improvement for any blocked head. The dominance chain is: T2 < T3 < T3+T6 < T4+T6 < T5+T6.
2. **MNV4-H1 and MNV4-H2 are immediate GO.** Train orientation and skew now, regardless of tier strategy. Both heads have adequate data and strong empirical validation (skew val MAE 0.837, beating DocAlign benchmark of 1.2).
3. **No tier achieves full 22-head production readiness in 12 weeks.** Even T5+T6 leaves 14 heads in the 30-59 needs-work range. Realistic expectation management is essential.
4. **Handwriting (G4) is the highest-risk group across all strategies.** Structural blockers (ILLEGIBLE void, MIXED_TYPED_HW absence, bimodal presence distribution) cannot be resolved by any computational enhancement alone.

### Top 5 Immediate Actions

| Priority | Action | Effort | Impact | Consensus |
|----------|--------|--------|--------|-----------|
| P0 | Fix 3 architectural defects (N_A sentinel, code_cls rename, skew derivation) | 1-2 days | Unblocks all training | 4/4 unanimous |
| P0 | Decide deployment model (SaaS vs. distributed) | 1 day | Determines license strategy | 4/4 unanimous |
| P0 | Initiate sd7k/wsrd license resolution (email authors) | 1 day | Unblocks shadow head | 4/4 unanimous |
| P1 | Execute E11 v3 completion (190K to 350K images) | 4-5 days | Unblocks script classifier | 3/4 majority |
| P1 | Execute E01 shadow severity labeling (sd7k/wsrd paired GT) | 1-2 days | Unblocks shadow head | 4/4 unanimous |

### Top 5 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CC-BY-SA-4.0 incompatible with distributed deployment model | Medium | CRITICAL | Legal review by week 2; maintain MIT-only fallback path |
| sd7k/wsrd license unresolvable (authors unresponsive) | Medium | HIGH | Replace with synthetic shadow from v3 (8K) + doc3d (MIT) |
| v3 generator bug harder to fix than expected | Low | HIGH | Cap at 190K; add MDIW13/MLT-19 as backup sources |
| SigLIP 8-week training convergence failure | Medium | MEDIUM | Reduce to 8 heads; extend timeline to 12 weeks |
| G4 handwriting data acquisition delays | High | LOW (deferred) | Release 2 planning absorbs delay |

### Recommended Phasing Strategy

- **Phase 0 (Weeks 1-2)**: Fix architectural defects + resolve deployment model + initiate legal reviews
- **Phase 1 (Weeks 2-4)**: Train MNV4-Conv-S with 3 heads on T4 data (orientation 50K, skew 90K, resolution quality 15K)
- **Phase 2 (Weeks 4-8)**: Execute E11 + E01; train SigLIP core 11 heads (G1 IQA + G2 Script + G5 Page Attrs); freeze backbone during warmup
- **Phase 3 (Weeks 8-12)**: Integrate G3 geometry heads; execute E03 (warping) + E05 (RQ V2); expand to 16 active heads
- **Phase 4 (Weeks 12+, Release 2)**: Integrate T5 handwriting data; synthesize ILLEGIBLE class; train G4 heads; teacher pseudo-labeling on production data
- **Parallel Track (Weeks 1-12)**: T5 data acquisition (KHATT, CASIA-HWDB2, IIIT-HW-Hindi) + legal review + OOD corpus expansion (2,985 to 12,000 images)

---

## Section 1: Current State Assessment

### 1.1 Architecture Recap

The production pipeline deploys two models in sequence, serving 22 training heads across 5 semantic groups.

**Model 1 -- MobileNetV4-Conv-Small (MNV4)**

- Parameters: approximately 4 million
- Inference budget: approximately 3 ms GPU
- Role: Pre-correction gate -- classifies orientation, estimates skew angle, and scores resolution quality before any geometric correction is applied
- Heads: 3 (MNV4-H1 orientation_cls, MNV4-H2 skew_reg, MNV4-H3 resolution_quality_reg)

**Model 2 -- SigLIP 2 NAFlex (SIG)**

- Parameters: approximately 88 million
- Inference budget: approximately 50 ms GPU
- Role: Full multi-task analysis on corrected images -- IQA scoring, script classification, post-correction geometry verification, handwriting characterization, and page attribute detection
- Heads: 19 across Groups G1-G5

**Head inventory by group:**

| Group | Label | Heads | Head IDs |
|-------|-------|-------|----------|
| MNV4 | MobileNetV4 pre-correction | 3 | MNV4-H1, MNV4-H2, MNV4-H3 |
| G1 | IQA (Image Quality Assessment) | 6 | SIG-G1-1 through SIG-G1-6 |
| G2 | Script detection | 1 | SIG-G2-1 |
| G3 | Post-correction geometry | 2 | SIG-G3-1, SIG-G3-2 |
| G4 | Handwriting characterization | 5 | SIG-G4-1 through SIG-G4-5 |
| G5 | Page attribute detection | 5 | SIG-G5-1 through SIG-G5-5 |

### 1.2 Dataset Inventory Summary

The project maintains a 62-dataset inventory (51 source datasets documented; 10 training datasets assembled or in progress; 1 OOD evaluation corpus). Audit status as of 2026-02-24:

**Source dataset pool:**

| Tier | Count | Image Volume | Audit Status |
|------|-------|--------------|--------------|
| MIT-compatible (commercial) | 33 datasets | approximately 2.1M images | Layer 2 metadata: 20/46 datasets enriched |
| NC/SA/TOU gray zone | 3 datasets (kuzushiji 481K, hiertext 11K, midv2020 4K) | approximately 0.5M additional | Available under non-commercial terms |
| TOU/NC expanded | approximately 22 datasets | approximately 0.5M additional | T3 scope |
| Unknown license (blocking) | 3 datasets (sd7k 7.2K, wsrd 4.5K, warpdoc 1.0K) | approximately 12.7K | License unconfirmed -- must contact authors |

**Training datasets assembled:**

| Dataset | Head(s) | Images Assembled | Status |
|---------|---------|-----------------|--------|
| orientation | MNV4-H1, SIG-G3-1 | 50,000 | Assembled; non-Latin coverage less than 1% |
| skew | MNV4-H2 | 90,412 | Assembled; 79.1% synthetic (cap violation) |
| synth-multiscript-v3 | SIG-G2-1 | 190,485 | Partial (generator stopped at 190K vs. 350K target) |
| IQA Phase 1 curated | SIG-G1-1 through G1-6 | 16,300 (hard labels) | VLM labeling 200/5,500 (3.6% complete) |
| IQA Phase 2 synthetic | SIG-G1-1 through G1-5 | 0 | Not assembled |
| resolution quality | MNV4-H3, SIG-G5-5 | 5,499 (DIQA-5000 only) | 18% of 30K minimum |
| handwriting | SIG-G4-1 through G4-5 | 38,967 dry-run (not assembled) | Multiple P0 blockers |
| shadow | SIG-G5-2 | 0 | Labeling script does not exist |
| warping | SIG-G5-3 | 0 | Severity formula undefined; labeling script does not exist |
| code detection | SIG-G5-4 | 8,613 dry-run (not assembled) | Rename fix + full run needed |
| capture method | SIG-G5-1 | 39,893 source records | 3 of 7 classes near-zero |

**Notable correction (2026-02-24):** doc3d (102K images with 3D mesh warping ground truth) is confirmed MIT-licensed, reversing a prior assumption that it was NC-SA-blocked. This dataset is now available in all commercial scenarios and is critical for SIG-G5-3 (warping_reg).

### 1.3 HAR Synthesis: Mean Readiness

The Head Adequacy Review (HAR) process independently scored all 22 heads using a rubric specific to each head's domain and data requirements. Summary statistics from HAR_SYNTHESIS.md:

| Metric | Value |
|--------|-------|
| Total heads reviewed | 22 |
| Ready (score >= 75, no P0 gaps) | 0 |
| Needs work (score 50-74, or resolvable P0 gaps) | 13 |
| Blocked (score < 50, or unresolvable P0 gaps) | 9 |
| Total P0 gaps across all heads | 72 |
| Heads with 0 P0 gaps | 4 (MNV4-H1, MNV4-H2, SIG-G3-1, SIG-G3-2) |
| Median HAR score | 39/100 |
| Lowest score | 14/100 (SIG-G4-5 legibility_reg) |
| Highest score | 65/100 (SIG-G1-5 compression_score) |

No head is ready for training. The four heads with zero P0 gaps (the Geometry batch) are closest to ready but score below 75 due to OOD design gaps and diversity dimension deficiencies.

**HAR scores vs. D1-D6 matrix scores (current column):**

The HAR rubric and the D1-D6 matrix rubric produce somewhat different absolute scores because the HAR uses head-specific methodology while the matrix applies a uniform 6-dimension framework. The current-state D1-D6 scores (from the scoring matrix) range from 13 (SIG-G5-2, SIG-G5-3) to 42 (MNV4-H1), with a mean of approximately 27/100.

**Only MNV4-H1 and MNV4-H2 are immediately trainable** by either rubric, and only with documented limitations (non-Latin coverage less than 1%; synthetic cap violation for H2).

### 1.4 Three Architectural Defects

Three schema and configuration defects are present in the current codebase. These are on the critical path and must be resolved before any training labels are generated. They do not affect which tier is chosen -- they are constant overhead across all scenarios. Estimated total effort: 3-5 hours.

**Defect 1: N_A Sentinel Value (CRITICAL)**

- Location: Handwriting assessment scaffold across all parsers
- Problem: The sentinel value for "no handwriting present" (N_A) encodes as `0.0` for regression heads (presence_reg, legibility_reg). This is semantically identical to "fully absent/illegible," which is wrong. Any training label generated before this fix is permanently corrupted -- the model learns that absence equals zero output.
- Heads affected: SIG-G4-1, SIG-G4-2, SIG-G4-3, SIG-G4-4, SIG-G4-5 (all five handwriting heads)
- Fix: Change sentinel to `-1.0`; apply masked loss (ignore samples where label equals -1.0 during backpropagation)
- Effort: 1-2 hours

**Defect 2: code_reg Misclassified as Regression (HIGH)**

- Location: Head registry, training script, inference code
- Problem: The head `code_reg` is configured with MSE loss and MAE metric, but the task is binary classification (has_code: 0 or 1). MSE on a binary target is suboptimal; calibration metrics are meaningless.
- Heads affected: SIG-G5-4
- Fix: Rename to `code_cls`; switch loss to binary cross-entropy; switch metrics to AUC and F1
- Effort: 1-2 hours

**Defect 3: SIG-G3-2 Skew Derivation Conflict (MEDIUM)**

- Location: Skew angle derivation for post-correction residual
- Problem: The derivation currently uses `abs(skew_angle)`, producing an unsigned regression target. MNV4-H2 trains on signed angles. The design intent for SIG-G3-2 (whether it predicts signed or unsigned residual) is not documented, creating ambiguity.
- Heads affected: SIG-G3-2
- Fix: Explicit design decision document specifying signed vs. unsigned semantics, followed by implementation alignment
- Effort: 30 minutes decision + 1 hour implementation

### 1.5 OOD Corpus Status

The OOD evaluation corpus targets 12,000-15,000 images across 9 categories to support production validation of all 22 heads.

**Current status (OOD_COVERAGE_GAP_REPORT.md, 2026-02-24):**

- Acquired: 2,985 images
- Target: 12,000 images (minimum) to 15,000 images (full specification)
- Progress: 24.9%
- The minimum viable P0 gate is passed -- directional evaluation is feasible. Statistically rigorous evaluation requires approximately 12,000 images.

Two P0 metric errors are documented in CORPUS_OOD_REVIEW_REPORT.md:

1. The ILLEGIBLE OOD floor uses classification accuracy as the metric, which is invalid when the model has zero training examples for that class. The correct metric is OSR Energy Score rejection rate (threshold: >= 70%).
2. MNV4-H1 uses raw softmax confidence for abstention decisions. Energy Score is required for overconfident transformer architectures.

These metric errors mean that even heads that achieve production training readiness (such as MNV4-H1 and MNV4-H2) cannot be properly evaluated against OOD data without first correcting the evaluation methodology. OOD collection should proceed in parallel with training data preparation rather than sequentially after it.

### 1.6 Current Acceptance Criteria Status

Of the 11 acceptance criteria in UNIFIED_TRAINING_CORPUS.md Section 11, as evaluated in CORPUS_OOD_REVIEW_REPORT.md:

| Criterion | Status | Detail |
|-----------|--------|--------|
| Minimum training samples at required label tier | FAIL | IQA 16.3K vs. 50-100K minimum; SIG-G3-2 has no narrow-range dataset; ILLEGIBLE class at 0 samples |
| Wild condition requirements | FAIL | 6 of 8 Section 8 requirements have zero meeting evidence |
| Label confidence floor | FAIL | VLM SRCC 0.53; gate at 0.65 not met; no halt condition defined |
| IQA compound distortion sub-split (Phase 1B) assembled | FAIL | Not assembled |
| v3 Arabic class balance within 3x constraint | FAIL | Arab at 3.78x target; exceeds 3x maximum |
| Shadow and warping real data assembled | FAIL | 0 real images assembled for both heads; L2 severity labeling pending |
| Synthetic mixing cap compliance | AT RISK | Skew at 79.1% synthetic vs. <= 37.5% ideal |
| Script x degradation cross-tabulation | AT RISK | 12 shadow/warping cells blocked |
| Wild condition: compound distortion >= 10% of IQA Phase 1B sub-split | FAIL | Sub-split not assembled |
| Wild condition: ambiguous orientation >= 2% labeled | FAIL | orientation_ambiguous class absent in 50K training set |
| Wild condition: ILLEGIBLE class >= 5% handwriting (>= 1,000 samples) | FAIL | 0 ILLEGIBLE samples |

**Summary: 6 FAIL, 2 AT RISK, 3 not yet assessable** due to upstream blockers.

**Phase 1 readiness:** MNV4-H1 (orientation) and MNV4-H2 (skew) can train with documented limitations. MNV4-H3 (resolution quality) is blocked pending V2 algorithm implementation and OHR-Bench/RealDAE labeling.

---

## Section 2: Tier Definitions and Constraint Analysis

### 2.1 Tier Specifications

Five tiers were evaluated. T6 is a modifier applied on top of any base tier rather than a standalone strategy.

**T2: Commercial Clean (MIT)**

- Dataset scope: 33 MIT-compatible datasets, approximately 2.1 million images. Excludes anyphotodoc6300 (GPL), financebench (NC), and muharaf (NC).
- Labeling policy: Existing labels only. No new labeling scripts executed. No schema defect fixes.
- Engineering effort: Near-zero for data engineering; legal review only.
- Key constraint: The license filter does not address any labeling pipeline gap. Blocked heads remain blocked because the labeling scripts do not exist, not because the datasets are unavailable.

**T3: Non-Commercial Expanded**

- Dataset scope: T2 plus SA-gray zone datasets (kuzushiji 481K, hiertext 11K, midv2020 4K) plus TOU/NC datasets, approximately 3.1 million images total.
- Labeling policy: Existing labels only. No new scripts.
- Engineering effort: License compliance review only.
- Key constraint: Same as T2. The additional 1 million images do not fix labeling pipeline gaps. Adding kuzushiji does not implement `label_shadow_severity.py`.

**T4: Enriched Current**

- Dataset scope: T3 scope (same image pool).
- Labeling policy: Run all currently-implemented labeling scripts. Fix all three architectural schema defects. Complete L2 enrichment for all datasets with existing pipelines.
- Engineering effort: Approximately 8-12 weeks across all heads (non-parallel; parallelizable to 4-6 weeks).
- Key constraint: T4 can only execute scripts that already exist. It cannot create the +/-2 degree narrow-range skew dataset (SIG-G3-2), collect ILLEGIBLE handwriting examples (SIG-G4-2), or source MIXED_TYPED_HW examples (SIG-G4-3).

**T5: Targeted Collection**

- Dataset scope: T4 scope plus new dataset acquisitions and new ground truth annotation.
- Labeling policy: T4 actions plus new engineering: ILLEGIBLE data collection pipeline, MIXED_TYPED_HW curation, SCANNER_ADF heuristics, FAX synthesis, harmonized cross-dataset labels.
- Engineering effort: 8-16 additional weeks beyond T4 for the G4 handwriting group and SIG-G3-2.
- Key constraint: Cost and timeline. T5 acquires what T4 cannot. Full G4 remediation is the long-tail item (8-12 weeks beyond T4 for complete harmonization).

**T6: Computational Enhancement**

- Dataset scope: Applied on top of any base tier (T2 through T5).
- Methods: 13 computational enhancements (CE-01 through CE-13), including synthetic generation pipelines, VLM labeling at scale, pseudo-labeling, augmentation pipelines, and domain-specific labeling scripts.
- Engineering effort: Varies per CE from 0.5 days (CE-09 V2 algorithm on v3 images, once V2 is implemented) to 3 weeks (CE-11 VLM IQA labeling at scale).
- Key constraint: T6 amplifies whatever base tier provides. T6 applied to T2 or T3 adds volume but still cannot fix underlying labeling gaps for blocked heads.

### 2.2 Available Datasets Per Tier

| Tier | Datasets | Image Volume (approximate) | Key Additions vs. Prior Tier |
|------|----------|---------------------------|-------------------------------|
| T2 (MIT commercial) | 33 | 2.1M | Baseline |
| T3 (NC/SA/TOU) | 55+ | 3.1M (+1M) | kuzushiji (481K), hiertext (11K), midv2020 (4K), financebench (54K), muharaf (25K) |
| T4 (Enriched Current) | Same as T2 or T3 | Same pool | Labels only -- no new image volume |
| T5 (Targeted Collection) | T4 plus new acquisitions | T4 plus 60-150K new images | KHATT (1.6K HW), IIIT-HW-Hindi (95K -- already in repo), CASIA-HWDB2 (52K chars -- already in repo), new ILLEGIBLE collection pipeline, +/-2 degree skew dataset built from scratch |
| T6 (CE overlay) | Any base tier | +50-150K synthetic images | CE-05: 50K IQA synthetic; CE-12: 102K doc3d warping labels; CE-03/04: 13K shadow/warping views already generated |

### 2.3 Dominated Strategy Identification

Consensus Round 2 (unanimous, 4/4 models) established the following dominance ordering:

```text
T2 < T3 < T3+T6 < T4+T6 < T5+T6   (quality ordering)
```

**T2 is dominated by T3.** T3 adds dataset volume at comparable legal complexity for non-commercial model distribution. There is no scenario in which T2 is preferred over T3 except for strict commercial model release requirements -- and even then, the training data licensing and model distribution licensing are separable questions.

**T3 is dominated by T3+T6.** T3 and T4 share the same image pool; T3 withholds labeling scripts. T3+T6 applies computational enhancements without the full T4 labeling effort. However, the practical cost of T4 labeling over T3+T6 is marginal -- the labeling scripts already exist and need to be executed, not built.

**T3+T6 is dominated by T4+T6.** The cost difference between running T4 labeling scripts (which are already implemented) and not running them is approximately 4-6 weeks of GPU VM time plus engineering coordination. The score improvement across blocked heads makes this cost unambiguously worthwhile.

**Key insight: T2 and T3 are inert tiers for training readiness.** The blocked heads (SIG-G4-2, SIG-G4-5, SIG-G5-2, SIG-G5-3, SIG-G3-2, and others) are blocked on labeling pipeline gaps and missing scripts -- not on data volume. Adding kuzushiji (481K) or muharaf (25K Arabic handwriting) does not cause `label_shadow_severity.py` to exist. License tier selection has near-zero impact on training readiness for the 9 fully blocked heads.

This does not mean the license analysis is irrelevant -- it is directly relevant to model distribution strategy and commercial deployment. The finding is that license filtering and training readiness are largely decoupled concerns that should be addressed on separate decision tracks.

**T4+T6 vs. T5+T6 ROI:** T4+T6 achieves approximately 80% of the quality ceiling of T5+T6 at approximately 50% of the cost (consensus Round 2, DeepSeek R1 and Grok 4 estimates). T5+T6 is not dominated but is the recommended Phase 2 overlay -- begin T5 acquisition in parallel with T4 execution rather than sequentially.

---

## Section 3: 22-Head x 5-Tier Scoring Matrix

### 3.1 Scoring Methodology (D1-D6)

Each head is scored on six dimensions plus a P0 bonus, for a maximum of 100 points.

| Dimension | Criterion | Full Score |
|-----------|-----------|------------|
| D1 | Sample count >= minimum specified in Section 2 | 10 (prorated if partial) |
| D2 | Synthetic percentage <= cap specified in Section 3 | 10 (0-7 if violation) |
| D3 | Label quality: > 80% of samples at confidence >= 0.6 | 10 (0-5 if VLM bottleneck or SRCC gate fails) |
| D4 | Diversity: >= 7 of 14 dimensions represented | 10 (6-8 if 5-6 dims; 0-4 if < 5 dims) |
| D5 | Wild conditions: all applicable Section 8 requirements met | 10 (prorated) |
| D6 | Cross-head conflicts: none unresolved | 10 (-2 to -5 per unresolved conflict) |
| P0 Bonus | Zero P0 gaps present | +40 maximum |

**Total maximum: 100 points.**

**Grade thresholds:**

- Blocked: score < 30 (marked as blocked in the heatmap)
- Needs work: score 30-59
- Near ready: score 60-74
- Ready: score 75-100

**Tier delta logic:**

- T2 to T3: adds dataset volume via NC/TOU/SA-gray datasets; labeling stays the same
- T3 to T4: executes existing scripts (resolves L2 field gaps, fixes schema defects, runs all existing pipelines)
- T4 to T5: acquires new data and builds new pipelines (ILLEGIBLE handwriting, MIXED_TYPED_HW, SCANNER_ADF heuristics, FAX synthesis)
- T6: computational enhancements applied on top of any base tier; each CE targets specific heads

### 3.2 Full Scoring Heatmap: 22 Heads x 5 Tiers

**Grade key:** blocked < 30 | needs work 30-59 | near ready 60-74 | ready 75-100

| Head | Task | Current | T2 | T3 | T4 | T5 | T4+T6 |
|------|------|---------|----|----|----|----|-------|
| **MNV4-H1** | orientation_cls | 42 | 42 | 42 | 52 | 60 | **68** |
| **MNV4-H2** | skew_reg | 32 | 32 | 32 | 42 | 50 | **52** |
| **MNV4-H3** | resolution_quality_reg | 28 | 28 | 28 | 50 | 58 | **68** |
| **SIG-G1-1** | blur_score | 35 | 35 | 37 | 47 | 55 | **82** |
| **SIG-G1-2** | noise_score | 35 | 35 | 37 | 47 | 55 | **82** |
| **SIG-G1-3** | contrast_score | 35 | 35 | 37 | 47 | 55 | **82** |
| **SIG-G1-4** | skew_score | 27 | 27 | 29 | 39 | 47 | **74** |
| **SIG-G1-5** | compression_score | 35 | 35 | 37 | 47 | 55 | **82** |
| **SIG-G1-6** | overall_quality | 31 | 31 | 33 | 43 | 51 | **76** |
| **SIG-G2-1** | script_cls | 40 | 40 | 42 | 52 | 65 | **72** |
| **SIG-G3-1** | orientation_cls (post-correction) | 40 | 40 | 40 | 50 | 58 | **62** |
| **SIG-G3-2** | skew_reg (post-correction, +/-2 degrees) | 20 | 20 | 20 | 32 | 55 | **40** |
| **SIG-G4-1** | presence_cls | 29 | 29 | 31 | 40 | 58 | **52** |
| **SIG-G4-2** | legibility_cls | 17 | 17 | 19 | 29 | 50 | **32** |
| **SIG-G4-3** | content_type_cls | 29 | 29 | 31 | 40 | 55 | **50** |
| **SIG-G4-4** | presence_reg | 29 | 29 | 31 | 40 | 52 | **50** |
| **SIG-G4-5** | legibility_reg | 18 | 18 | 20 | 30 | 48 | **38** |
| **SIG-G5-1** | capture_cls | 30 | 30 | 32 | 48 | 68 | **64** |
| **SIG-G5-2** | shadow_reg | 13 | 13 | 15 | 45 | 55 | **75** |
| **SIG-G5-3** | warping_reg | 13 | 13 | 15 | 40 | 50 | **68** |
| **SIG-G5-4** | code_cls | 30 | 30 | 32 | 55 | 70 | **71** |
| **SIG-G5-5** | resolution_quality_reg | 26 | 26 | 26 | 48 | 56 | **66** |

### 3.3 Grade Distribution by Tier

| Tier | Blocked (<30) | Needs Work (30-59) | Near Ready (60-74) | Ready (75-100) | Trainable Head Count |
|------|--------------|-------------------|-------------------|----------------|----------------------|
| Current | 8 | 14 | 0 | 0 | 2 (MNV4-H1, MNV4-H2 only) |
| T2 | 8 | 14 | 0 | 0 | 2 |
| T3 | 7 | 15 | 0 | 0 | 2 |
| T4 | 2 | 18 | 2 | 0 | approximately 6 |
| T5 | 0 | 14 | 7 | 1 | approximately 12 |
| T4+T6 | 0 | 9 | 7 | 6 | All 22 unblocked |

**T4 is the minimum viable unlock tier.** T2 and T3 produce no meaningful improvement for any blocked head. T4 moves 6 heads from blocked status and produces the first non-zero ready and near-ready counts. T4+T6 achieves 13 heads at 60 or above -- the threshold at which SigLIP 2 Warmup phase training can begin for those head groups.

### 3.4 Per-Group Narrative Highlights

#### Group MNV4 -- Most Actionable Group, One Intractable Constraint

MNV4-H1 (orientation_cls) and MNV4-H2 (skew_reg) are the only two immediately trainable heads across all 22. Both can proceed this week with documented limitations.

MNV4-H1 scores 42 at current state and 68 at T4+T6. The binding constraint is non-Latin coverage below 1% in the 50K training set -- the orientation_ambiguous class is entirely absent. T4 (Stream 4C orientation sub-command execution) addresses both. T6 CE-07 (script rebalancing) contributes diversity. Neither T4 nor T4+T6 reaches the ready threshold of 75; T5 acquisitions (KHATT, CASIA-HWDB negatives) are needed for full compliance.

MNV4-H2 (skew_reg) has the most striking discrepancy between empirical performance and compliance score: the 90K training set achieves val MAE 0.837 degrees, SRCC 0.936, and 99.5% orientation accuracy, yet scores only 32/100 on the D1-D6 matrix. The entire discrepancy is D2: the synthetic percentage is 79.1% against a 37.5% cap. This cap violation is structural -- assembling 50,000+ natural scans at confidence >= 0.7 is practically infeasible with the current dataset inventory, even at T5. The recommended disposition is to document this as an incidental violation (not a data quality failure), proceed with Phase 1 bootstrap using the strong empirical metrics as justification, and accept that full D2 compliance requires a future natural scan acquisition campaign. T4+T6 brings the score to only 52 because CE-10 (compound distortion) helps D5 but does not address the D2 cap.

MNV4-H3 (resolution_quality_reg) is blocked at 28 (current) due to having labeled only 5,499 of 30,000 minimum images (18%). T4 is the unlock tier: running `label_resolution_quality.py` on OHR-Bench (8,500 images) and RealDAE (1,200 images), combined with the V2 Sauvola+projection algorithm that reduces IQR from 9.0px to the 2-3px target, brings the score to 50 (needs work). T4+T6 with CE-09 (V2 algorithm on v3 images, approximately 5K additional labeled) reaches 68 (near ready).

#### Group G1 -- High T6 Leverage, VLM Bottleneck on G1-6

All six IQA heads share the same training dataset. The shared dataset state is 16,300 Phase 1 hard-label images with Phase 2 pseudo-labels (target: 100,000) at 0% assembled. The VLM labeling pipeline has scored 200 of 5,500 DIQA-5000 images (3.6%) with SRCC 0.53 -- below the 0.65 gate.

Four heads (G1-1 blur, G1-2 noise, G1-3 contrast, G1-5 compression) achieve identical scores of 82 at T4+T6 because CE-05 (50,000-image JPEG/blur/noise synthetic pipeline) resolves the D1 sample count gap, and CE-10 (compound distortion generation) resolves D5. These four heads have augmentation-parameter labels (exact, from the synthetic generation process), which gives clean D3 scores. The result is the highest score achievable by any IQA head without T5 acquisitions.

G1-4 (skew_score) is the outlier in this group: D3 carries a penalty because the derivation methodology is undefined (IQA skew quality score is not the same construct as geometric skew angle), and D6 carries a penalty for the unresolved cross-head conflict with MNV4-H2 and SIG-G3-2. T4+T6 achieves 74 -- just inside near-ready -- contingent on documenting the IQA-skew construct as an OCR degradation proxy (not a Hough angle).

G1-6 (overall_quality) is the hardest of the six. The VLM SRCC of 0.53 (0.39 all-image; 0.53 non-rotated) fails the 0.65 gate. Consensus Round 1 is unanimous: VLM labels at SRCC 0.53 cannot be used for regression training. The ceiling SRCC achievable by a model trained on such labels is 0.45-0.60, which would not meet production requirements. T4+T6 scores 76 (ready), but this is entirely contingent on CE-11 (VLM IQA labeling at scale with prompt v2.0) achieving SRCC > 0.60 on a 30-50 image validation set before scaling. If prompt v2.0 fails the gate, G1-6 stays at approximately 50 in the best case.

#### Group G2 -- Ready with Three Blocking Decisions

SIG-G2-1 (script_cls) scores 40 at current state and 72 at T4+T6 -- near ready. The head has adequate data volume (190,485 v3 synthetic plus 753 MDIW13 real images), but three specific decisions are blocking T4 action:

1. Cher (Cherokee) and Cans (Canadian Aboriginal Syllabics) font audit -- must determine whether available fonts produce realistic document images
2. Armn (Armenian) and Grek (Greek) GCS audit -- must resolve keep-vs-delete decision for these script classes
3. Kore to Hang rename -- Korean classification must align with ISO 15924 Hang code

Additionally, the Arabic (ARAB) class is 3.78 times the target, violating the 3 times maximum constraint. Weighted resampling to cap Arabic at 13,000 images, combined with CE-07 (script rebalancing) for rare scripts, resolves D6. Four scripts (TIBT, KHMR, SINH, JAVA) have zero real images -- synthetic generation for these classes is the T5 action; T4+T6 tolerates their absence at reduced D4 score.

The script classifier benefits critically from the frozen-backbone finding in Consensus Round 1: with a frozen SigLIP 2 backbone (linear probe only), 50-100 samples per class may be sufficient. Full fine-tune requires 2,500-5,000 samples per class. This finding means G2-1 is effectively ready for training with frozen backbone approach at T4+T6 despite class imbalance.

#### Group G3 -- Split Outcome: G3-1 Unlockable, G3-2 Structurally Blocked

SIG-G3-1 (orientation_cls, post-correction) shares the 50K orientation dataset with MNV4-H1. It scores identically across all tiers through T4. The post-correction variant introduces a cascade architecture concern -- training on the same data as MNV4-H1 reduces the independent validation value of the post-correction verification step. T4+T6 achieves 62 (near ready), the same actions as MNV4-H1 apply.

SIG-G3-2 (skew_reg, post-correction, +/-2 degrees narrow-range) is the most structurally distinct head in the matrix. Its current score of 20 reflects a fundamental issue: the +/-2 degree narrow-range dataset (approximately 20,000 images) does not exist at all. D1 is zero not because labeling is incomplete but because the dataset has never been built. No existing script creates this dataset. T4 (which runs existing scripts) brings D1 to 0 -- unchanged. T6 CEs do not address this either. T4+T6 achieves only 40 (needs work) because all other dimensions are adequate and partial P0 bonus accrues, but D1 remains unresolved.

**T5 is the minimum viable tier for G3-2.** The +/-2 degree dataset must be built from scratch by synthetically rotating clean DocLayNet, SROIE, and Arabic documents at 0.5-2 degree increments. Effort: 2-3 weeks. Even at T5, the score reaches only 55 (needs work); T5+T6 approaches 65 (near ready).

#### Group G4 -- Highest-Risk Group, No Tier Achieves Ready

The five handwriting heads share the same 60K target dataset. All five are blocked, and the group has the worst outcome across all tier scenarios. Even T5+T6 leaves the group's best head (G4-1) at 58 (needs work) and its worst (G4-5) at 48 (needs work).

The group has two categories of structural blocker that no labeling investment can resolve within a 12-week horizon:

**Category A: Data that does not exist and cannot be derived from existing corpora**

- ILLEGIBLE handwriting class: approximately 0 examples exist because all curated handwriting corpora exhibit curation bias toward legible examples. A dedicated VLM-guided selection pipeline from OCR-rejected documents is required. Effort: 3-5 weeks.
- MIXED_TYPED_HW class: approximately 0 natural examples exist across all candidate datasets. Hospital admission forms, government forms with handwritten fills, and OCR-rejected hybrid pages are the required source. Effort: 4-6 weeks.
- Mid-range handwriting presence scores (0.2-0.7): fewer than 3,000 examples exist. The distribution is bimodal -- 0.0 for printed documents and approximately 0.95 for pure handwriting corpora.

**Category B: Performance targets that exceed inter-annotator agreement (IAA) ceilings**

- G4-2 (legibility_cls): the F1 >= 0.72 target is unreachable given an IAA ceiling of 60-70% for legibility classification. Target revision to F1 >= 0.60 is mandatory.
- G4-5 (legibility_reg): the Pearson r >= 0.80 target exceeds the IAA-derived theoretical ceiling of approximately 0.60-0.65. Target revision to r >= 0.55 with a monotonicity constraint is mandatory.

Additionally, the N_A sentinel defect (Defect 1 from Section 1.4) must be fixed before any handwriting labeling begins. Labels generated with the 0.0 sentinel are permanently corrupted.

The G4 group requires T5 acquisition as a prerequisite for meaningful progress, with G4-1 requiring KHATT (1.6K Arabic handwriting) and IIIT-HW-Hindi (95K -- already in repo per project memory). G4-2 and G4-5 require dedicated data collection pipelines that are 3-5 weeks of engineering work independent of any existing codebase.

#### Group G5 -- Highest Single-Action Leverage in the Matrix

The five page attribute heads span the widest range of outcomes and contain the highest-leverage individual actions in the entire matrix.

SIG-G5-2 (shadow_reg) scores 13 at current state (fully blocked, 0 images assembled) and 75 at T4+T6 -- the largest single improvement in the matrix. The entire delta is attributable to one missing script: `label_shadow_severity.py`. This script needs to extract shadow severity from the sd7k (7,239 images) and wsrd (4,500 images) paired ground truth using the formula `mean(abs(shadow_img - clean_img)[shadow_mask]) / 255.0`. Implementation effort is 3-4 days on a GPU VM. CE-01 formalizes this as a computational enhancement; CE-03 populates sidecars for the 8,000 shadow views already generated from v3. With T4 labeling and CE-01/CE-03, G5-2 reaches 75 (ready). One unresolved constraint: sd7k and wsrd have unconfirmed licenses. Without author confirmation, these datasets are treated as all-rights-reserved for model card disclosure purposes (usable for internal training).

SIG-G5-3 (warping_reg) is in the same blocked state (13/100, 0 assembled) but has an additional prerequisite: the 3D mesh to scalar severity formula must be defined before any implementation can proceed. The recommended formula is `clip(k * std(Z_grid_normalized), 0.0, 1.0)`. Once defined, `label_warping_severity.py` can be implemented and run on doc3d (102,000 images) -- a confirmed MIT-licensed dataset. CE-02 and CE-12 apply the formula at scale. T4+T6 achieves 68 (near ready). The formula decision is a zero-cost domain decision that is the prerequisite for all subsequent work.

SIG-G5-4 (code_cls, formerly code_reg) scores 30 at current state. The architectural defect (Defect 2 from Section 1.4) accounts for the D6 score of 0. Renaming the head to code_cls and switching from MSE to BCE resolves D6. A dry-run has already produced 8,613 records (86% of the 10,000 target). After fixing negative contamination validation from multimodal_textbook and enforcing the style ratio (>= 70% printed code in document vs. screenshots), a full generation run completes the D1 requirement. T4 alone achieves 55 (needs work); T4+T6 achieves 71 (near ready). This head has the fastest path to improvement of any currently blocked head.

SIG-G5-1 (capture_cls) and SIG-G5-5 (resolution_quality_reg) reach 64 and 66 respectively at T4+T6, both in near-ready range. G5-1 requires the 6-class schema decision (merging CAMERA_PROFESSIONAL and CAMERA_SMARTPHONE) and SCANNER_ADF heuristic labeling from RVL-CDIP. G5-5 shares the resolution quality labeling work with MNV4-H3.

### 3.5 Performance Delta Estimates (Consensus Round 1)

Consensus Round 1 consulted four models (Gemini 2.5 Pro, Gemini 3 Pro Preview, DeepSeek R1, Grok 4) on six calibration topics. The following estimates apply when planning tier decisions.

**IQA Regression at 50% Minimum Samples (16.3K vs. 25K+ target):**

| Metric | Degradation Estimate | Source |
|--------|---------------------|--------|
| MAE increase | +25-45% (median approximately 35%) | Consensus median of 4-model range |
| SRCC ceiling | 0.60-0.75 (from approximately 0.85 target) | All 4 models agree insufficient for production |
| Kendall weighting benefit | 5-10% improvement | Cannot compensate for data deficit |

The pseudo-label absence (0/100K) is the dominant factor. All four models agree: 16.3K hard labels alone are insufficient for production deployment of the IQA regression heads.

**VLM Labels at SRCC 0.53:**

All four models unanimously reject VLM labels at SRCC 0.53 for regression training. The ceiling SRCC achievable by a model trained on such labels is 0.45-0.60 -- the model cannot exceed teacher quality. The consensus gate threshold is SRCC >= 0.65 (compromise between the 0.60 and 0.70 positions held by different models). The recommended fallback if SRCC < 0.65 is binning to 3 coarse classes (Good/Okay/Bad) for classification rather than regression.

**Script Classifier with 8.6x Class Imbalance:**

The consensus finding depends critically on backbone strategy:

- Frozen SigLIP 2 backbone (linear probe): 50-100 samples per class may be sufficient; 80-92% accuracy achievable
- Full fine-tune: 2,500-5,000 samples per class needed; 65-84% accuracy

With 108K balanced training data (approximately 5,700 per class after rebalancing): the head is ready for the frozen backbone approach. Focal loss plus oversampling is recommended by all four models regardless of strategy.

**Synthetic vs. Annotated for Geometry:**

All four models agree synthetic labels are superior to human-annotated labels for geometric tasks (orientation, skew). The reasons are:

- Tier-0 labels (mathematically derived from rotation parameters) are exact -- zero annotation noise
- Human labels would actually degrade accuracy for geometry tasks
- Domain gap (synthetic vs. natural) is addressed by 21-50% natural image injection
- The MNV4-H2 result (val MAE 0.837 degrees, beating the DocAlign benchmark of 1.2 degrees) validates this approach

**Phased Training with Zero-Shot Heads (consensus: proceed, 3/4):**

Three of four models recommend proceeding with phased training even when some heads lack data. The recommended precaution is freezing the backbone during warmup (first 5 epochs) to prevent feature drift -- the one dissenting model (Gemini 3 Pro Preview) flagged backbone drift as the primary risk. Kendall uncertainty weighting automatically down-weights heads with absent or poor-quality data.

**Minimum Viable Training Corpus (consensus):**

- Minimum 3 diverse semantic groups represented
- Regression heads: 15,000-25,000 samples minimum for Phase 1
- Classification heads: 1,000-5,000 samples per class
- Warmup gate: val SRCC > 0.65 (IQA); accuracy > 75% (Script)
- Expand gate: all active heads stable (loss variance < 0.1)

### 3.6 T6 Computational Enhancement Mapping

The 13 T6 CEs have targeted impact. The table below maps each CE to the heads it primarily unblocks and the score impact measured from T4 base.

| CE | Description | Primary Heads | Score Impact from T4 Base |
|----|-------------|---------------|---------------------------|
| CE-01 | Shadow severity labeling from sd7k/wsrd paired GT | SIG-G5-2 | +30 |
| CE-02 | Warping severity from doc3d 3D mesh | SIG-G5-3 | +28 |
| CE-03 | Synthetic shadow from v3 images (8K already generated; needs sidecars) | SIG-G5-2 | +5 (D1 top-up) |
| CE-04 | Synthetic warping from v3 images (5K already generated; needs sidecars) | SIG-G5-3 | +5 (D1 top-up) |
| CE-05 | JPEG/blur/noise synthetic pipeline (50K images) | SIG-G1-1, G1-2, G1-3, G1-5 | +35 (D1 unlock) |
| CE-06 | Parallel distortion pipeline (contrast, compression variants) | SIG-G1-3, G1-5 | +5 (D4) |
| CE-07 | Script rebalancing (Arab cap + rare script fill) | SIG-G2-1 | +20 |
| CE-08 | Handwriting label harmonization across datasets | SIG-G4-1, G4-2, G4-3, G4-4, G4-5 | +10 per head |
| CE-09 | Resolution quality V2 (Sauvola+projection algorithm on v3 images) | MNV4-H3, SIG-G5-5 | +18 each |
| CE-10 | Compound distortion generation (shadow+blur, warp+noise, etc.) | All G1, SIG-G5-2, SIG-G5-3 | +5 (D5) |
| CE-11 | VLM IQA labeling at scale (requires prompt v2.0 SRCC > 0.60 validation first) | SIG-G1-6 primarily | +33 (if SRCC gate passed) |
| CE-12 | doc3d mesh-derived warping at scale (102K images with severity labels) | SIG-G5-3 | +8 (D1 scale-up) |
| CE-13 | Capture method heuristic labeling (ADF and FAX detection) | SIG-G5-1 | +16 |

**CE dependency ordering (must be respected):**

1. CE-09 V2 algorithm must be implemented before applying CE-09 to v3 images
2. CE-11 requires prompt v2.0 validation on 30-50 test images before scaling to 2,000-5,000
3. CE-01 and CE-02 labeling scripts must be written (T4 actions) before CE-03/CE-04 can populate sidecars
4. CE-07 requires three blocking decisions resolved (Cher/Cans font audit, Armn/Grek GCS audit, Kore to Hang rename)
5. CE-08 requires N_A sentinel fix (Defect 1) before any handwriting label harmonization

### 3.7 Key Finding: T4 as Minimum Unlock Tier

The scoring matrix confirms the following group-level mean scores across tiers, with T4 producing the first meaningful improvement for every blocked group:

| Head Group | Current Mean | T4 Mean | T4 Delta | T4+T6 Mean |
|------------|-------------|---------|----------|------------|
| MNV4 | 32.7 | 47.3 | +14.6 | 62.7 |
| G1 (IQA) | 32.3 | 42.3 | +10.0 | 79.7 |
| G2 (Script) | 40.0 | 52.0 | +12.0 | 72.0 |
| G3 (Geometry, post-correction) | 30.0 | 41.0 | +11.0 | 51.0 |
| G4 (Handwriting) | 24.4 | 35.8 | +11.4 | 44.4 |
| G5 (Page Attributes) | 22.4 | 47.2 | +24.8 | 68.8 |

**Largest T4 improvements (single-head):**

| Head | Current | T4 | T4 Delta | Primary Action |
|------|---------|----|---------|----|
| SIG-G5-2 (shadow_reg) | 13 | 45 | +32 | Implement `label_shadow_severity.py` |
| SIG-G5-3 (warping_reg) | 13 | 40 | +27 | Define formula + implement `label_warping_severity.py` |
| SIG-G5-4 (code_cls) | 30 | 55 | +25 | Rename fix (1 hour) + full generation run |
| MNV4-H3 (resolution_quality_reg) | 28 | 50 | +22 | V2 algorithm + OHR-Bench/RealDAE labeling |

**What T4 cannot fix:**

- SIG-G3-2 D1 (+/-2 degree dataset does not exist -- must be built from scratch)
- SIG-G4-2 ILLEGIBLE class void (no curated corpus contains ILLEGIBLE examples)
- SIG-G4-5 score range coverage (inherits G4-2 structural gap)
- SIG-G4-3 MIXED_TYPED_HW class (no natural source corpus exists)

**Key conclusion:** T4+T6 achieves 13 heads at 60 or above, which is the threshold for SigLIP 2 Warmup phase training. T4+T6 achieves 6 heads at 75 or above (G1-1, G1-2, G1-3, G1-5, G1-6, G5-2) -- the first ready-grade scores in the entire analysis. The seven heads that T4+T6 cannot unlock to ready grade are SIG-G3-2, SIG-G4-1 through SIG-G4-5, and SIG-G4-4 (structural or acquisition gaps requiring T5). These seven heads are all in the Handwriting group or the post-correction narrow-range geometry head.

---

## Section 4: Licensing Impact Analysis

### 4.1 Overview

The 22 training heads (MobileNetV4-Conv-S x 3, SigLIP 2 NAFlex x 19) draw from 62 source
datasets. License compatibility was assessed under three progressively permissive scenarios:

- **S1 (MIT-clean)**: CC-BY-4.0, CDLA, PD, and MIT only; excludes ShareAlike gray zone, NC,
  GPL, and all Research-TOU datasets.
- **S2a (CC-BY-SA-4.0)**: S1 plus ShareAlike gray-zone datasets (kuzushiji, hiertext,
  midv2020); model released under CC-BY-SA-4.0.
- **S3 (CC-BY-NC-SA-4.0)**: S2a plus NC datasets (financebench, muharaf); academic distribution
  only.

Legal posture throughout is conservative: training is treated as producing a derivative work.
Research-TOU datasets (e.g., IAM, OHR-Bench, DIQA-5000) are classified separately as
breach-of-contract risk rather than copyright incompatibility.

### 4.2 Per-Head Licensing Sensitivity

#### 4.2.1 Head Impact Matrix

| Head | Model | S1 Status | S2a Status | Critical Datasets Lost Under S1 |
|------|-------|:---------:|:----------:|----------------------------------|
| MNV4-H1 orientation_cls | MNV4 | **GREEN** | GREEN | None -- TOU sources not needed given 616K clean pool |
| MNV4-H2 skew_reg | MNV4 | **YELLOW** | GREEN | IAM (130K TOU, 7 heads), OHR-Bench (16K TOU), RVL-CDIP (16K TOU), FintabNet (97K TOU), SmartDoc-QA (4.3K TOU) |
| MNV4-H3 resolution_quality | MNV4 | **RED** | YELLOW | DIQA-5000 (5.5K TOU), OHR-Bench (8.5K TOU), RealDAE (1.2K TOU) -- all three are the labeling pool |
| SIG-G1-1 blur | SigLIP | **RED** | RED | DIQA-5000 (TOU), OHR-Bench (TOU) -- structural TOU dependency for all IQA annotations |
| SIG-G1-2 noise | SigLIP | **RED** | RED | Same as G1-1 |
| SIG-G1-3 contrast | SigLIP | **RED** | RED | Same as G1-1 |
| SIG-G1-4 skew_severity | SigLIP | **RED** | RED | Same as G1-1 |
| SIG-G1-5 compression | SigLIP | **RED** | RED | Same as G1-1 |
| SIG-G1-6 overall_quality | SigLIP | **RED** | RED | Same as G1-1 |
| SIG-G2 script_cls | SigLIP | **YELLOW** | GREEN | Kuzushiji (481K, SA gray), MDIW13 (290K TOU), IIIT-HW-Hindi (95K TOU), SIW13 (16K TOU), CASIA-HWDB2 (5K TOU), Yarmouk (15K TOU) |
| SIG-G3-1 orientation_cls | SigLIP | **GREEN** | GREEN | Same pool as MNV4-H1 |
| SIG-G3-2 skew_reg | SigLIP | **YELLOW** | GREEN | Same as MNV4-H2 |
| SIG-G4-1 hw_presence | SigLIP | **RED** | YELLOW | IAM (130K TOU), Muharaf (25.7K NC-blocked) |
| SIG-G4-2 hw_legibility | SigLIP | **RED** | YELLOW | Same as G4-1 |
| SIG-G4-3 hw_content_type | SigLIP | **RED** | YELLOW | Same as G4-1 |
| SIG-G4-4 hw_presence_reg | SigLIP | **RED** | YELLOW | Same as G4-1 |
| SIG-G4-5 hw_legibility_reg | SigLIP | **RED** | YELLOW | Same as G4-1 |
| SIG-G5-1 capture_cls | SigLIP | **GREEN** | GREEN | RVL-CDIP (16K TOU) -- substitutable; RealDAE (1.2K TOU) -- minor |
| SIG-G5-2 shadow_reg | SigLIP | **RED** | RED | SD7K (7.2K unknown license), WSRD (4.5K unknown license) -- unknown blocks real-data component |
| SIG-G5-3 warping_reg | SigLIP | **YELLOW** | YELLOW | AnyPhotoDoc6300 (6.3K GPL-blocked), WarPDoc (1K unknown), SmartDoc-QA (4.3K TOU) |
| SIG-G5-4 code_cls | SigLIP | **RED** | RED | GitHub-code-snippets (unacquired; license unknown) |
| SIG-G5-5 resolution_quality_reg | SigLIP | **RED** | YELLOW | Same as MNV4-H3 |

#### 4.2.2 Status Summary by Scenario

| Status | S1 Count | S2a Count | Notes |
|--------|:--------:|:---------:|-------|
| GREEN | 4 | 6 | Orientation (2), Capture Method (1), Script (1 in S2a) |
| YELLOW | 3 | 6 | Skew (2), Script (S1), multiple in S2a |
| RED | 15 | 10 | IQA (6), Handwriting (5), Resolution (2), Shadow (1), Code (1) |

**Critical observation**: 15 of 22 heads are RED under S1 not because of hard copyright
incompatibility, but because the primary IQA and quality-annotation labels originate from
Research-TOU datasets (DIQA-5000, OHR-Bench, RealDAE, IAM). These are breach-of-contract
risks, not copyright violations, and carry different mitigation pathways.

### 4.3 Hard-Blocked Datasets and Replacement Adequacy

Three datasets are hard-blocked under S2a (the recommended scenario):

#### AnyPhotoDoc6300 -- GPL-3.0 -- 6,306 images -- Warping Head

GPL-3.0 is incompatible with a CC-BY-SA-4.0 model release; copyleft would propagate to all
derivative works, disqualifying enterprise deployment. Replacement: **doc3d (MIT, 102,064
images)**. Doc3d provides richer labels -- 3D mesh geometry, depth maps, UV coordinates, and
surface normals -- from which warping severity scalars are derived via the formula
`severity = clip(k * std(Z_grid_normalized), 0, 1)`. The replacement is not merely adequate;
doc3d provides superior label richness compared to AnyPhotoDoc6300's paired 2D ground truth.
Net training impact: **positive**.

#### FinanceBench -- CC-BY-NC-4.0 -- 54,121 images -- Not in pipeline

FinanceBench does not appear in any current training dataset's `l4_source_datasets` frontmatter.
Its NC block has zero training impact. DocLayNet (CDLA-P) and PubTabNet (CDLA-S) provide
adequate financial document coverage for all heads that require it.

#### Muharaf -- CC-BY-NC-SA-4.0 -- 25,711 images -- Handwriting Heads (G4-1 through G4-5)

Muharaf is the only source of Arabic cursive handwriting (historical manuscript style) in the
current dataset inventory. Its NC clause is incompatible with commercial distribution under any
permissive scenario. Replacement candidates: arabic-docs (CC-BY, 10K) and Yarmouk (TOU, 15K).
Assessment: **poor**. Arabic-docs covers Arabic-script text but represents modern web documents,
not historical cursive. Yarmouk (Research-TOU) partially covers the gap but is itself a Tier B
risk. The G4 handwriting heads will have reduced Arabic cursive coverage under all commercial
scenarios. This is the only hard block with no clean substitute.

#### Replacement Adequacy Summary

| Blocked Dataset | Replacement | Adequacy | Net Impact |
|-----------------|-------------|:--------:|------------|
| AnyPhotoDoc6300 (GPL, 6.3K) | doc3d (MIT, 102K) | SUPERIOR | Positive -- richer labels, 16x more images |
| FinanceBench (NC, 54K) | DocLayNet + PubTabNet | N/A | No impact -- not in pipeline |
| Muharaf (NC, 25.7K) | Arabic-docs + Yarmouk | POOR | Negative -- Arabic cursive HW gap |

### 4.4 ShareAlike Gray-Zone Datasets

Under S1 (MIT-clean), three CC-BY-SA datasets are excluded as a gray-zone precaution. Under
S2a (CC-BY-SA model license), these datasets are fully resolved.

| Dataset | License | Images | Heads Benefiting | Replacement Under S1 | Replacement Adequacy |
|---------|---------|-------:|-----------------|----------------------|----------------------|
| Kuzushiji | CC-BY-SA-4.0 | 481,336 | G2 script (JPAN), G4 handwriting | Synth-multiscript-v3 Jpan (11,995 images) | POOR for HW (historical cursive not approximable); ADEQUATE for script detection |
| HierText | CC-BY-SA-4.0 | 11,641 | MNV4-H2/G3-2 skew, G4 handwriting | COCO-Text (CC-BY-4.0, 43.7K) | GOOD -- COCO-Text provides equivalent coverage at 3.8x the volume |
| MIDV2020 | CC-BY-SA-2.5 | ~4,000 | G5-1 capture_cls (scanner class) | MIDV500 (MIT, 15K) | GOOD overall; minor gap in flatbed-paired capture diversity |

Accepting S2a unlocks **+496,977 images** (kuzushiji 481K + hiertext 11.6K + midv2020 4K)
that directly address the two lowest-scoring head groups: script detection and handwriting.

### 4.5 Research TOU Risk Tiers

Research-TOU datasets are scored on three weighted dimensions: Legal Exposure (0.40), Industry
Precedent (0.35), and Training Criticality (0.25). Composite scores produce four tiers.

**Tier Definitions**:

- **Tier A (0.0-3.0 -- Accepted Practice)**: Widely used in released models; enforcement risk
  negligible; industry consensus treats as usable.
- **Tier B (3.1-5.0 -- Low Risk)**: Common usage; some TOU ambiguity; legal review recommended
  before commercial release.
- **Tier C (5.1-7.0 -- Moderate Risk)**: More restrictive TOU; less precedent; active
  enforcement possible; legal opinion required.
- **Tier D (7.1-10.0 -- Avoid)**: High enforcement risk; institutional claimant with track
  record; explicit commercial restrictions.

#### Tier C Datasets (Action Required)

| Dataset | Composite Score | Images | Heads Fed | Primary Concern |
|---------|:--------------:|-------:|:---------:|-----------------|
| DIQA-5000 | **5.93** | 5,500 | 8 (all IQA/RQ heads) | Explicit research-only TOU; only validated IQA labels in system; authors are the institutional claimant |
| OHR-Bench | **5.75** | 16,091 | 8 (all IQA/RQ heads) | CC-BY-4.0 published license conflicts with "research intent" language in README; legal ambiguity unresolved |
| IAM | **5.28** | 130,212 | 7 (skew natural scans + all 5 handwriting heads) | Univ. of Bern holds copyright; active licensing program; explicit prohibition on commercial use and redistribution |
| RVL-CDIP | **5.35** | 16,000 | 6 (orientation, skew, capture, warping) | IIT-CDIP archive; academic TOU; industry broadly uses without incident but scale of exposure creates risk on model card |

#### Tier B Dataset Summary (18 datasets)

MDIW13 (4.80), FintabNet (4.45), IIIT-HW-Hindi (4.43), TibHCR (4.25), CASIA-HWDB2 (4.23),
SIW13 (4.13), SmartDoc-QA (4.00), TableBank (4.00), SROIE (4.00), PUCIT-OHUL (3.88),
Yarmouk (3.88), ReaLDAE (3.75), CVSI (3.75), SigNaTR6K (3.30), Dibco (3.30), MLE2E (3.45),
KHATT (3.38), Tobacco800 (3.90). All carry low enforcement risk given industry precedent.

No datasets meet Tier D criteria given current enforcement track records.

### 4.6 Unknown License Datasets -- Resolution Priority

| Dataset | Images | Heads | Resolution Urgency | Action |
|---------|-------:|-------|:------------------:|--------|
| **SD7K** | 7,239 | G5-2 shadow_reg | **P0 CRITICAL** | Email Yun et al. (CVPR 2021) for MIT grant -- likely permissive; shadow head blocked without resolution |
| **WSRD** | 4,500 | G5-2 shadow_reg | **P0 CRITICAL** | Email authors -- likely permissive; together with SD7K constitutes the only real camera-shadow pool |
| **WarPDoc** | 1,020 | G5-3 warping_reg | P1 HIGH | Check GitHub/paper for LICENSE file (15 minutes); CVPR/ICCV papers often default to MIT |
| **DocAlign12K** | ~12,000 | G5-3 warping NONE class | P2 LOW | Alternatives exist (DocLayNet + RVL-CDIP); low priority |
| DRCCBI, Q-Doc, OmniDocBench, SROIE-Voxel51 | various | None (not in any l4_source_datasets) | P3 DEFERRED | Not in training pipeline; skip |

Until SD7K and WSRD license status is resolved, the shadow head (G5-2) cannot train on real
camera-shadow examples. The fallback is doc3d (MIT) + v3 synthetic (MIT) only, producing
approximately 8K real + 8K synthetic images -- sufficient to meet the 15K target but with
reduced camera-shadow domain diversity.

### 4.7 Commercial Viability Decision Tree

```text
What is the intended distribution model?
|
+-- INTERNAL ONLY (no external release, no API)
|   +-- TOU risk minimal; any scenario is workable.
|       Recommendation: S2a or proceed without formal license posture.
|
+-- EXTERNAL RELEASE or PUBLIC API
    |
    +-- Commercial use required?
    |   |
    |   +-- NO (academic distribution only)
    |   |   +-- Use S3 (CC-BY-NC-SA-4.0)
    |   |       Gains: Muharaf (25.7K Arabic cursive HW)
    |   |       Cost: Forfeits all commercial use for you and downstream users
    |   |
    |   +-- YES (commercial use required)
    |       |
    |       +-- Is historical Japanese HW or kuzushiji-cursive coverage needed?
    |       |   |
    |       |   +-- YES: Use S2a (CC-BY-SA-4.0) [RECOMMENDED]
    |       |   |   Gains: +496,977 images (kuzushiji, hiertext, midv2020)
    |       |   |   Obligation: Derivatives must be CC-BY-SA-4.0; attribution required
    |       |   |
    |       |   +-- NO: Use S1 (MIT)
    |       |       Replace kuzushiji with synth-v3 Jpan (11,995 images)
    |       |       Replace hiertext with COCO-Text (CC-BY-4.0)
    |       |       Replace midv2020 with MIDV500 (MIT)
    |       |       Consequence: Handwriting heads lose only historical Japanese HW source
    |       |
    |       +-- GPL (S2b) -- AVOID in all cases
    |           Doc3d (MIT, 102K) dominates AnyPhotoDoc6300 (GPL, 6.3K)
    |           GPL copyleft renders model commercially unusable for enterprise
    |
    +-- Tier C TOU action (applies to all commercial scenarios)
        IAM: Obtain written permission from Univ. Bern OR replace with COCO-Text + HASy + NIST
        OHR-Bench: Confirm CC-BY-4.0 interpretation supersedes "research intent" language
        DIQA-5000: Contact authors for commercial research license
        RVL-CDIP: Document in model card; industry precedent supports continued use
```

### 4.8 Recommendation: CC-BY-SA-4.0 as Optimal License Posture

The analysis supports adopting **S2a (CC-BY-SA-4.0)** as the model license for the first
public release.

**Rationale**:

1. **Kuzushiji is irreplaceable for handwriting heads**: 481,336 historical Japanese images
   cannot be synthetically approximated for G4 handwriting detection. The G4 heads are already
   the weakest head group (avg HAR 22); accepting kuzushiji under CC-BY-SA-4.0 is the
   difference between marginally adequate and severely inadequate handwriting coverage.

2. **Commercial viability is preserved**: CC-BY-SA-4.0 permits commercial use by the developer
   and downstream users. The SA clause is standard in the ML ecosystem and widely accepted.
   CLIP (OpenAI), DINOv2 (Meta), and numerous HuggingFace foundation models have been trained
   on CC-BY-SA data and released under Apache/MIT without enforcement action.

3. **Hard-blocked count is unchanged**: The three hard-blocked datasets (AnyPhotoDoc6300 GPL,
   FinanceBench NC, Muharaf NC) remain blocked in S2a just as in S1. No additional exclusions
   apply.

4. **Doc3d replaces AnyPhotoDoc6300 with a net quality improvement**: The MIT-licensed doc3d
   dataset (102K images with 3D mesh geometry labels) is superior to AnyPhotoDoc6300 (6.3K
   paired 2D GT) in label richness and volume. Excluding the GPL source carries no cost.

5. **Net image gain over S1**: +496,977 images directly addressing the two hardest-hit head
   groups (script detection and handwriting).

**License-orthogonal actions (required regardless of scenario)**:

- Email SD7K and WSRD authors for explicit license grant (P0, Day 3).
- Seek legal opinion on OHR-Bench CC-BY-4.0 vs. "research intent" interpretation (P0, Day 7).
- Request commercial research license from DIQA-5000 authors (P1, Day 14).
- Contact IAM database administrators (Univ. Bern) for commercial training permission (P1, Day 7).

---

## Section 5: Computational Enhancement Catalog

### 5.1 Overview

This catalog documents 20 computational enhancement methods identified for improving training
data quality and coverage across all 22 heads without acquiring new external datasets. Methods
are organized by implementation phase, ranging from immediate zero-cost schema fixes through
post-training active learning.

### 5.2 Label Quality Ladder (5-Tier System)

All labels in the training pipeline are classified by confidence and assigned training weights
accordingly.

| Tier | Name | Confidence Range | Training Weight | Examples |
|------|------|:---------------:|:---------------:|---------|
| 0 | **Exact / By Construction** | 1.0 | 1.0 | Rotation-by-construction orientation labels; Augraphy severity parameter as shadow label; doc3d Z_grid to warping severity; JPEG quality parameter to compression score |
| 1 | **Human Annotation** | 0.85-0.99 | 0.9 x conf | DIQA-5000 MOS labels (crowdsourced); KHATT Arabic handwriting legibility; manual warping severity spot-check (50 samples for formula calibration) |
| 2 | **Model / Heuristic Labels** | 0.50-0.84 | 0.8 x conf x (1/std) | VLM IQA scoring (SRCC 0.53 V1); Hough-derived skew labels (conf >= 0.70 gate); resolution quality V1 CC measurement |
| 3 | **Heuristic / Rule-Based** | 0.40-0.65 | 0.6 x conf | PaddleOCR confidence to resolution proxy; Hough line count to skew presence; script detection via Unicode character ranges |
| 4 | **Inferred / Inherited** | 0.25-0.50 | 0.4 x conf | Dataset-level domain label inherited as per-image label; script_family from dataset-level annotation; resolution tier from known DPI range |

**Loss weighting convention**: Per-sample loss weight = `base_weight * tier_weight * conf_modifier`,
where `conf_modifier = min(1.0, label_confidence / confidence_threshold)`. Regression heads
additionally multiply by `1 / label_std` to weight precise labels higher. Tier 4 labels are
restricted to pre-training and curriculum learning warm-up; they must be replaced by Tier 0-2
before final training.

**Minimum confidence thresholds by head type**: Classification (4-class orientation): Tier 1
kappa >= 0.75; (19-class script): Tier 2 per-class F1 >= 0.70. Continuous regression (skew,
resolution): Tier 2 std <= 1.0 degrees/10px, SRCC >= 0.60. Severity regression (shadow, warping):
Tier 0 SRCC >= 0.70 in calibration spot-check; Tier 2 SRCC >= 0.55. IQA regression:
Tier 2 SRCC >= 0.50; reject below 0.40.

### 5.3 Full Enhancement Catalog

#### Phase 0 -- Schema Fixes (Days 1-2, Zero GPU Cost)

**E -- Schema Fixes**

These are not enhancement methods but prerequisite defect resolutions that gate downstream
assembly. Two schema defects currently block the handwriting heads entirely.

**N_A Sentinel (G4-1 hw_presence blocker)**: The current schema has no representation for
documents that are ambiguously-not-handwritten (e.g., printed forms where a few fields are
blank). Adding `hw_presence_na` as a sentinel class resolves the G4-1 blocker with one schema
edit and no data changes. Effort: 0.5 days.

**ILLEGIBLE void (G4-2 hw_legibility blocker)**: The legibility regression head has no
defined label range for fully illegible samples. Defining the ILLEGIBLE bucket as the
[0.0-0.05] range resolves the convention ambiguity. Effort: 1 day.

**code_cls rename**: The G5-4 head is named `code_reg` in the head status table but `code_cls`
in the training dataset documentation. Consistent naming is required before any integration
scripts reference the schema field. Effort: 2 hours.

**Skew natural-scan decision (synthetic cap)**: MNV4-H2 and G3-2 skew datasets are at 79%
synthetic composition, exceeding the stated 60% synthetic cap from the corpus mixing policy.
A documented decision is required -- either accept the cap exceedance or identify which natural
scan sources to add -- before skew dataset metadata is finalized. Effort: decision meeting only.

#### Phase 1 -- Quick Wins (Days 3-7)

**E17 -- Capture Method Dataset Assembly (3-Class)** | ROI: 3.96 (rank 1)

Run `prepare_multitask_datasets.py source` in full mode. The dry-run already validated
correctly: 39,893 records returned (camera: 19,893 / born_digital: 10,000 / scanned: 10,000).
The only change required is removing the `--dry-run` flag. Heads unblocked: G5-1 capture_cls
(HAR 17 to 60). Data volume: 39,893 images. Label quality: Tier 2 (from L2 `capture_method`
field) for camera/scanned; Tier 0 by construction for born_digital. Effort: 0.5 days.
GPU cost: < 1 hour (metadata write-back only).

**E01 -- Shadow Severity Labeling -- Paired GT** | ROI: 1.51 (rank 2)

Execute `scripts/label_shadow_severity.py` against SD7K (7,239 images) and WSRD (4,500 images).
Severity formula: `mean(abs(shadow - clean)[mask]) / 255`, computed from the paired clean
reference. Writes `physical_degradation.shadow_severity` to L2 metadata. Expected yield:
approximately 11,700 labeled images after confidence >= 0.70 filtering. Label quality: Tier 0 (exact -- paired
ground truth). Effort: 1 day. GPU cost: 3-4 hours on A100. Dependency: SD7K/WSRD license
resolution (P0). This enhancement is blocked until SD7K and WSRD license status is confirmed;
the script already exists.

**E02 -- NONE-Class Shadow Construction** | ROI: 0.39 (chains with E01)

Sample clean reference images from SD7K/WSRD paired GT, SmartDoc-QA clean frames (approximately 2K),
MIDV500 flat captures (approximately 1K), and v3 clean views (approximately 500). Assign `shadow_severity=0.0` explicitly.
Breaking the dataset-identity confound is necessary to prevent the model from learning
"SD7K-style images = shadow present" rather than luminance contrast. Expected yield: 7,000-8,500
NONE-class images. Label quality: Tier 0. Effort: 1 day. Dependency: E01 must complete first
to confirm paired-GT path conventions.

**E09 -- v3 Shadow Views Execution (8K Synthetic)** | ROI: 0.39 (rank 11)

Execute the existing `generate_v3_shadow_view.py` script against the v3 GCS pool to produce
8,000 shadow-augmented images across 4 shadow types: edge, cast, spotlight, scanner_lid.
One-line code fix required first: the script does not currently write Augraphy severity
parameters to L2 sidecars. Without this fix, the 8K images cannot be used by
`prepare_multitask_datasets.py shadow`. Effort: 1 day (1-hour code fix + 6 GPU-hours execution).
Dependency: E02 must establish NONE-class severity conventions first.

**E12 -- Orientation Hybrid Rebuild** | ROI: 0.53 (rank 8)

Execute `build_orientation_real_component.py` on DocLayNet PDFs (approximately 32K documents x 4 rotations)
and RVL-CDIP scans (approximately 12K documents x 4 rotations), then `derive_v3_orientation_view.py` for
non-Latin scripts (up to 20K from v3 pool). Assembles 50,000-image orientation dataset with >= 60%
real-document images. Primary quality gain: non-Latin coverage (Arabic, CJK, Devanagari)
increases from < 1% to approximately 30%. Scripts exist; execution is pending GCS data
transfer. Heads unblocked: MNV4-H1 (HAR 63 to 80), G3 orientation_post (HAR 46 to 65).
Effort: 2 days. GPU cost: approximately 8 hours.

#### Phase 2 -- Core Assembly (Days 8-15)

**E07 -- IQA Synthetic Pipeline (Augmentation-Parameter Labels)** | ROI: 1.15 (rank 4)

Implement the `prepare_multitask_datasets.py iqa` sub-command, which does not currently exist.
Generate approximately 100,000 synthetic IQA-labeled images from the v3 base pool using Augraphy and
Albumentations with augmentation parameters as Tier 0 labels: `blur_kernel_size` to blur score,
`noise_std` to noise score, `JPEG quality` to compression score, etc. Augmentation ordering
must place geometry transforms before degradation (already fixed in `generator.py`). This is
the primary path to unblocking all six G1 IQA heads. Heads unblocked: G1-1 through G1-6
(avg HAR 47 to 70). Expected yield: 100,000 images with 6 IQA labels per image. Label quality:
Tier 0. Effort: 3-5 days (implementation) + 20 GPU-hours (generation). Risk: medium
(sub-command architecture must match existing CLI conventions).

**E05 -- Resolution Quality V2 Labeling** | ROI: 0.40 (rank 10)

Upgrade `resolution_quality.py` with four algorithmic improvements: (A) Sauvola binarization
(`cv2.ximgproc.niBlackThreshold`, k=0.2) replacing Otsu threshold; (B) morphological closing
(3x1 horizontal + 1x3 vertical kernels to reconnect CJK radicals); (C) KDE mode estimation
replacing median for char-height estimation; (D) horizontal projection profiles as CJK-weighted
ensemble (0.7 projection / 0.3 CC for CJK; 0.3 projection / 0.7 CC for Latin). The V1
implementation produced median IQR of 9.0 px against a 2-3 px target; V2 is projected to
reduce IQR to 4-5 px. After implementation, re-label DIQA-5000 (5,500 images), OHR-Bench
(8,500 images), and RealDAE (1,200 images). Expected yield: approximately 15,200 labeled images at
improved precision. Label quality: Tier 2. Effort: 4 days code + 8 GPU-hours. Dependency:
`opencv-contrib-python` for `cv2.ximgproc`; PaddleOCR v2 (>=2.7, < 3.0) already operational
on Vultr A100 VM. Heads served: MNV4-H3 (HAR 26 to 55), G5-5 (HAR 26 to 55).

**E13 -- Handwriting Dataset Assembly (Multi-Script)** | ROI: 0.79 (rank 7)

Integrate three newly-acquired handwriting datasets whose integration scripts are already
present in the repository as untracked files: `integrate_khatt_enrichments.py` (KHATT:
approximately 9K Arabic cursive images), `integrate_casia_hwdb2_enrichments.py` (CASIA-HWDB2: Chinese
handwriting), and `integrate_iiit_hw_hindi_enrichments.py` (IIIT-HW-Hindi: Devanagari). After
L2 enrichment, assemble a 60,000-image handwriting training set with script-balanced sampling
across Latin (IAM, NIST), Arabic (KHATT), CJK (CASIA), and Devanagari (IIIT-HW). Prerequisites:
N_A schema defect (G4-1) and ILLEGIBLE void (G4-2) must be resolved first. Heads served:
G4-1 through G4-5 (avg HAR 22 to 55). Effort: 5 days total (1 GPU-day per enrichment run + 2
days assembly). Risk: high (schema defects gate this entire chain).

**E19 -- Multi-Column Skew Label Quality Gate** | ROI: 0.84 (rank 6)

The current 90K skew dataset contains multi-column pages where the Hough detector and
projection profile disagree by more than 0.5 degrees. These disagreements represent unreliable labels
that degrade training. Implement a cross-detector agreement gate: retain only samples where
both detectors agree within 0.5 degrees; discard or re-label disagreements. Also report skew MAE
separately for single-column vs. multi-column documents. Expected effect: removes 10-15%
of the 90K dataset but improves label quality for the remaining samples from Tier 2 to Tier 0
(single-detector agrees becomes dual-detector agrees = higher precision). Effort: 2 days.
GPU cost: approximately 2 hours. Heads served: MNV4-H2, G3 skew_post (HAR 55 to 72).

**E18 -- ILP Dataset Allocation Optimization** | ROI: 1.83 (rank 3)

Implement a PuLP or OR-Tools integer linear program with approximately 250 decision variables
(`x[source][dataset] = N samples`) and approximately 150 constraints encoding the 14-dimension
diversity requirements from `DATASET_DIVERSITY_REQUIREMENTS.md`. The optimizer allocates sample
counts across 25 source datasets and 10 training datasets to maximize aggregate diversity
coverage subject to target size, mixing cap, and domain balance constraints. No new images are
generated; existing samples are re-allocated to maximize coverage of underrepresented dimensions.
Expected gain: approximately 5% average diversity coverage improvement across all 22 heads. Effort: 3 days.
CPU cost: < 1 hour for LP solve. Dependency: Layer 2 metadata aggregates must be complete for
all source datasets. Heads served: All 22 (simultaneous improvement).

#### Phase 3 -- Advanced (Days 16-25)

**E03 -- Warping Severity Formula and doc3d Labeling** | ROI: 0.112 (rank 19, but on critical path)

Define the warping severity scalar formula from doc3d 3D mesh data:
`severity = clip(k * std(Z_grid_normalized), 0, 1)`, where k is calibrated on 50 manually
spot-checked samples with SRCC >= 0.70 acceptance gate. Secondary validation uses
`clip(max_displacement / document_diagonal, 0, 1)` with disagreements > 0.20 flagged for
review. After formula confirmation, implement `label_warping_severity.py` (stub exists in
untracked files) and run against 102K doc3d images. Stratified sampling produces approximately
20K images for the warping training dataset. Label quality: Tier 0 (3D mesh geometry is exact).
Effort: 11 days total (2-day formula design + 5-day script implementation + 4 GPU-hours run).
Risk: medium (formula calibration gate could extend timeline if SRCC < 0.70 on first attempt).
Heads served: G5-3 warping_reg (HAR 17 to 60).

**E11 -- v3 Completion Run (190K to 350K)** | ROI: 2.50 (adjusted to 1.25 for generator bug risk)

Complete the synth-multiscript-v3 generation run that stopped at 190,485 images. The generator
bug (memory exhaustion, GCS write error, or process termination -- root cause unconfirmed) must
be identified and fixed before resuming. Target composition: 35% single-script / 45%
two-script / 12% three-script / 8% four+. Completion would add approximately 160,000 images
(+84% over current pool) and resolve the 8.6x class imbalance in the script head. The expanded
v3 pool also serves as the base for E09 shadow views, E10 warping views, and the IQA synthetic
pipeline (E07). Expected yield: 160,000 new images. Effort: 2.5 days (bug fix + resume run).
GPU cost: 80-100 hours on A100 (approximately $28-35 on Modal). Risk: high (generator bug root cause
unknown). Heads served: G2 script (directly), G1-1 through G1-6 (expanded base pool),
G5-2 shadow (additional shadow views), G5-3 warping (additional warping views).

**E08 -- VLM IQA Re-Labeling with Prompt v2.0** | ROI: 0.148 (rank 18)

The V1 VLM labeling run on DIQA-5000 produced SRCC = 0.53 (non-rotated subset), below the
0.65 gate. Four root causes were identified: orientation-dependent scoring (VLM penalizes
rotation that DIQA-MOS ignores), score compression (only 11 unique values, 83% in 2.5-3.2
range), sub-score conflation (sharpness, noise, and contrast merged into a single overall
score), and domain-construction rotation confound (48% of Q5-highest-MOS images are rotated
90 degrees). Prompt v2.0 must address orientation independence and finer granularity. Validation
protocol: label 30-50 images with v2.0; if SRCC > 0.60, scale to 2,000-5,000 images; reject
and redesign if SRCC <= 0.60. All four consensus models unanimously rejected V1 labels (SRCC
0.53) for regression training. The V2 gate threshold is 0.65 SRCC (consensus compromise
between 0.60 and 0.70). If gate is not met, labels may be used in a coarse 3-class
classification (Good/Okay/Bad) rather than regression. Expected yield: 2,000-5,000 VLM-labeled
images for G1-6 overall_quality. Effort: 3 days. API cost: approximately $20-30 for 5K images. Heads
served: G1-6 overall_quality (HAR 37 to 55), supplementary for G1-1, G1-2, G1-3.

#### Phase 4 -- Post-Training (After First SigLIP 2 Training Run)

**E20 -- Active Learning Loop** | ROI: 0.396 (rank 12, deferred)

After the first complete SigLIP 2 training run, evaluate per-head validation loss and identify
failure clusters by diversity dimension (capture_method, script, domain, resolution tier,
color_mode, document_age). Trigger thresholds: any head with val_loss > 2x median; any
diversity dimension with error > 1.5x dataset-wide average. Generate targeted synthetic or
re-weighted real samples for failing (dimension, head) pairs. The `evaluate_by_dimension.py`
script required for failure analysis does not yet exist. Expected effect: 5-20% additional
improvement per failing head per active learning cycle. Effort: 10 days per full cycle (training, evaluation, targeted generation, and retraining). Risk: medium (failure cluster patterns
unknown until first run). Heads served: All 22 (post-training refinement).

### 5.4 Synthetic Generation Expansion Highlights

#### v3 Completion Run (E11)

The v3 generator stopped at 190,485 images. Completing the run to the 350K target provides
the single largest yield increase in the catalog (+160K images) and resolves the primary
script head bottleneck. All views derived from v3 (shadow, warping, orientation) scale
proportionally. The generator bug root cause must be determined before resuming; options include
memory exhaustion during GCS batch writes, process preemption on Modal, or a JPEG write error
at a specific composition threshold.

#### Font Diversity Expansion

Five script families are currently font-impoverished, limiting the visual diversity needed for
script detection and handwriting analysis:

| Script | Current Fonts (est.) | Target | Priority New Families |
|--------|:--------------------:|:------:|----------------------|
| TIBT (Tibetan) | 2-3 | 8+ | Jomolhari, Tibetan Machine Uni, DDC Uchen |
| THAI | 3-4 | 10+ | Sarabun, TH Sarabun New, Angsana Thai |
| KORE | 4-5 | 12+ | Nanum Gothic, Noto Sans KR, Malgun Gothic |
| INDIC_OTHER | 2-3 | 8+ | Noto Sans Sinhala, Khmer, Myanmar |
| ARAB | 6-8 | 15+ | Amiri, Noto Sans Arabic, Lateef, Reem Kufi |

Expected yield from font expansion: +20-30% script diversity coverage across underrepresented
classes. Effort: 3-5 days (font acquisition, generator config update, targeted re-generation).
Dependency: E11 completion run must complete first.

#### New Degradation Profiles

Eight new Augraphy-based degradation profiles address wild-condition gaps documented in the
head analysis reports:

| Profile | Augmenters | Severity Range | Heads Served |
|---------|-----------|:--------------:|:-------------|
| book_gutter_shadow | BookBinding + shadow gradient | 0.3-0.9 | G5-2 shadow (critical gap) |
| screen_recapture | BadPhotoCopy + moire simulation | 0.2-0.8 | G1-1 blur, G1-5 compression, G5-1 capture |
| adf_curl | Cylindrical warp (radius approximately 50px) | 0.1-0.7 | G5-3 warping |
| fax_artifacts | DirtyDrum + LowInkPeriodicLines + NoiseTexturize | 0.3-0.8 | G1-2 noise, G1-3 contrast, G1-5 compression |
| aged_historical | ColorPaper (yellow) + InkBleed + luminance reduction | 0.2-0.7 | G1-6 overall_quality |
| crumple_cockling | Folding (multi-fold) + paper_factory | 0.2-0.6 | G5-3 warping (WARP-G06) |
| nth_photocopy | JPEG-print-JPEG cycle N=3-5 | 0.3-0.7 | G1-1 blur, G1-2 noise, G1-5 compression |
| binarized_with_shadow | Sauvola binarization + shadow-region suppression | sentinel | G5-2 shadow (requires sentinel handling) |

Expected yield: 2,000-5,000 images per profile; 20,000-35,000 additional images total.
Effort: 2-4 days total. Dependencies: E09 (shadow write-back) and E03 (warping formula)
must be complete to assign compound labels correctly.

### 5.5 Per-Head Enhancement Coverage Matrix

The following matrix shows which of the 20 enhancements directly benefit each head:

| Head | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|:-------:|:-------:|:-------:|:-------:|:-------:|
| MNV4-H1 orientation | Schema | E12 | E18 | -- | E20 |
| MNV4-H2 skew | Skew decision | -- | E18, E19 | -- | E20 |
| MNV4-H3 resolution | -- | -- | E05, E18 | E06 | E20 |
| G1-1 blur | -- | -- | E07, E18 | E11, E14 | E20 |
| G1-2 noise | -- | -- | E07, E18 | E11, E14 | E20 |
| G1-3 contrast | -- | -- | E07, E18 | E11, E14 | E20 |
| G1-4 skew_severity | -- | -- | E07, E18, E19 | E11, E14 | E20 |
| G1-5 compression | -- | -- | E07, E18 | E11, E14 | E20 |
| G1-6 overall_quality | -- | -- | E07, E18 | E08, E11, E14 | E20 |
| G2 script | -- | -- | E18 | E11 | E20 |
| G3 orientation_post | Schema | E12 | E18 | -- | E20 |
| G3 skew_post | Skew decision | -- | E18, E19 | -- | E20 |
| G4-1 hw_presence | N_A fix | -- | E13, E18 | -- | E20 |
| G4-2 hw_legibility | ILLEGIBLE fix | -- | E13, E18 | -- | E20 |
| G4-3 hw_script | -- | -- | E13, E18 | -- | E20 |
| G4-4 hw_content_type | -- | -- | E13, E18 | -- | E20 |
| G4-5 hw_density | -- | -- | E13, E18 | -- | E20 |
| G5-1 capture_cls | -- | E17 | E18 | -- | E20 |
| G5-2 shadow_reg | -- | E01, E02, E09 | E18 | E11, E14, E15 | E20 |
| G5-3 warping_reg | Rename | E04, E10 | E18 | E03, E11, E14, E15, E16 | E20 |
| G5-4 code_cls | Rename | -- | E18 | -- | E20 |
| G5-5 resolution | -- | -- | E05, E18 | E06 | E20 |

### 5.6 Top 5 Enhancements by ROI

| Rank | ID | ROI Score | Rationale |
|-----:|----|-----------:|-----------|
| 1 | E17 | 3.96 | Dry-run already validated; zero blocking dependencies; executes in 0.5 days; immediately unblocks G5-1 capture_cls |
| 2 | E11 | 2.50 (adj. 1.25) | Largest image volume gain (+160K); resolves script class imbalance; expands base pool for all view-derived enhancements; penalized for generator bug risk |
| 3 | E18 | 1.83 | Zero new data; improves all 22 heads simultaneously; 3-day implementation; only prerequisite is L2 metadata completion |
| 4 | E01 | 1.51 | Script exists; 1-day execution; Tier 0 labels from paired GT; directly unblocks shadow head real-data component |
| 5 | E07 | 1.15 | Unblocks 6 G1 IQA heads simultaneously; 100K images at Tier 0 quality; represents the largest single block of currently-unassembled IQA data |

---

## Section 6: Priority Ranking by ROI

### 6.1 Ranked Enhancement Actions (Top 20)

The following ranking uses the formula:
`ROI = (heads_unblocked * mean_score_delta * log10(data_volume)) / (effort_days * risk_factor)`

where `risk_factor` is 1.0 (low), 1.5 (medium), or 2.0 (high).

| Rank | ID | Enhancement | Heads | Score Delta | Data Volume | Effort (days) | Risk | ROI |
|-----:|----|-----------:|:-----:|:-----------:|:-----------:|:-------------:|:----:|----:|
| 1 | E17 | Capture method assembly | 1 (G5-1, 17 to 60) | 0.43 | 39,893 | 0.5 | 1.0 | **3.96** |
| 2 | E11 | v3 completion run | 8+ (G2, G1 pool) | 0.30 | 160,000 | 2.5 | 2.0 | 2.50 |
| 3 | E18 | ILP allocation optimizer | 22 (all, +5% diversity) | 0.05 | all existing | 3.0 | 1.0 | **1.83** |
| 4 | E01 | Shadow severity labeling | 1 (G5-2, 28 to 65) | 0.37 | 11,700 | 1.0 | 1.0 | **1.51** |
| 5 | E07 | IQA synthetic pipeline | 6 (G1-1 to G1-6, avg 47 to 70) | 0.23 | 100,000 | 4.0 | 1.5 | **1.15** |
| 6 | E19 | Multi-column skew gate | 2 (MNV4-H2, G3-skew, 55 to 72) | 0.17 | 90,000 (clean) | 2.0 | 1.0 | 0.84 |
| 7 | E13 | Handwriting dataset assembly | 5 (G4-1 to G4-5, avg 22 to 55) | 0.33 | 60,000 | 5.0 | 2.0 | 0.79 |
| 8 | E12 | Orientation hybrid rebuild | 2 (MNV4-H1, G3-orient, 63 to 80) | 0.17 | 50,000 | 2.0 | 1.5 | 0.53 |
| 9 | E15 | Book gutter shadow augmentation | 2 (G5-2, G5-3 compound) | 0.08 | 1,000 | 1.0 | 1.0 | 0.48 |
| 10 | E05 | Resolution Quality V2 labeling | 2 (MNV4-H3, G5-5, 26 to 55) | 0.29 | 15,200 | 4.0 | 1.5 | 0.40 |
| 11 | E09 | v3 shadow views execution | 1 (G5-2 synthetic component) | 0.10 | 8,000 | 1.0 | 1.0 | 0.39 |
| 12 | E20 | Active learning loop | 22 (post-training refinement) | 0.08 | variable | 10.0 | 2.0 | 0.40 |
| 13 | E10 | v3 warping view write-back | 1 (G5-3 synthetic) | 0.05 | 5,000 | 0.5 | 1.0 | 0.37 |
| 14 | E02 | NONE-class shadow construction | 1 (G5-2, balanced NONE class) | 0.10 | 8,000 | 1.0 | 1.0 | 0.39 |
| 15 | E04 | NONE-class warping construction | 1 (G5-3, required for assembly) | 0.08 | 7,000 | 1.0 | 1.0 | 0.31 |
| 16 | E14 | Compound degradation augmentation | 8 (G1-1 to G1-6, G5-2, G5-3) | 0.05 | 500 | 3.0 | 1.5 | 0.24 |
| 17 | E06 | Synth-250K resolution teacher | 2 (MNV4-H3, G5-5, Tier 0 unlock) | 0.20 | 250,000 | 7.0 | 1.5 | 0.21 |
| 18 | E16 | ADF scanner curl augmentation | 1 (G5-3 enterprise gap) | 0.10 | 400 | 1.5 | 1.0 | 0.17 |
| 19 | E08 | VLM IQA re-labeling V2 | 1 (G1-6, 37 to 55) | 0.18 | 5,000 | 3.0 | 1.5 | 0.15 |
| 20 | E03 | Warping formula + doc3d labeling | 1 (G5-3, 17 to 60) | 0.43 | 20,000 | 11.0 | 1.5 | 0.11 |

**Notes on ranking interpretation**: E11 v3 completion run carries the highest adjusted ROI
(2.50) but the highest risk factor (generator bug unknown). Conservative planning should treat
E11's effective ROI as 1.25 (2.50 / risk-adjustment 2.0). E03 ranks last by pure ROI but
sits on the only critical path that cannot be shortened by any parallel execution: warping
formula design gates both warping assembly and all compound augmentation involving warp labels.

### 6.2 Critical Path Identification

Seven independent assembly chains are required to unblock all 22 heads. Chain length (days
to first training-ready dataset) is the primary scheduling constraint.

**Chain A: Shadow Assembly (G5-2) -- 6 days total**

```text
E01 label_shadow_severity.py (EXISTS -- execute)   [Day 2]
  +-- E02 NONE-class shadow construction             [Day 3-4]
        +-- E09 v3 shadow views (severity write-back) [Day 3-4, parallel]
              +-- [SHADOW ASSEMBLY] shadow sub-command [Day 5]
                    +-- E15 book gutter augmentation   [Day 5-6]
                          +-- [G5-2 TRAINING READY: 15K images]
```

**Chain B: Warping Assembly (G5-3) -- 11-13 days total (longest critical path)**

```text
E03 WARP-G02 formula definition (design decision)  [Day 2]
  +-- E03 label_warping_severity.py creation         [Days 4-5]
        +-- E04 NONE-class warping construction       [Days 8-9, parallel]
        +-- E10 v3 warping view write-back            [Days 8-9, parallel]
              +-- E03 doc3d 3D mesh labeling run      [Days 6-7, 4 GPU-hours]
                    +-- [WARPING ASSEMBLY] warping sub-command [Day 8-9]
                          +-- E16 ADF curl augmentation [Days 18-19]
                                +-- [G5-3 TRAINING READY: 20K images]
```

**Chain C: Resolution Quality (MNV4-H3, G5-5) -- 11+ days**

```text
E05 RQ V2 code upgrade                             [Days 10-11]
  +-- E05 RQ V2 labeling run (3 datasets)           [Days 11-12, 8 GPU-hours]
        +-- E06 Synth-250K teacher generation        [Days 22-24, 40 GPU-hours]
              +-- [Teacher model training]           [Days 24-25]
                    +-- [Pseudo-label real datasets] [Phase 4]
                          +-- [MNV4-H3, G5-5 PRODUCTION READY]
```

**Chain D: IQA Pipeline (G1-1 through G1-6) -- 5-9 days**

```text
E07 implement prepare_multitask_datasets.py iqa    [Days 5-6]
  +-- E07 execute 100K synthetic generation         [Days 9-10, 20 GPU-hours]
        +-- E08 VLM re-labeling V2 (if gate passes) [Days 16-17]
        +-- [G1-1 through G1-5 TRAINING READY]
              +-- [G1-6 TRAINING READY: synthetic + VLM real]
```

**Chain E: Script Head (G2) -- 2.5 days (if generator bug fix is fast)**

```text
E11 fix generator bug + resume v3 run              [Days 16-18, 100 GPU-hours]
  +-- [SCRIPT ASSEMBLY] script sub-command          [Day 18]
        +-- [G2 TRAINING READY: 108K images]
```

**Chain F: Orientation Rebuild (MNV4-H1, G3) -- 2 days**

```text
E12 execute orientation rebuild scripts            [Days 4-5, 8 GPU-hours]
  +-- [MNV4-H1, G3 TRAINING READY: 50K images]
```

**Chain G: Handwriting (G4-1 through G4-5) -- 7 days (after schema fixes)**

```text
Fix N_A schema defect                              [Day 1]
  +-- Fix ILLEGIBLE void                            [Day 1]
        +-- E13 run 3 integration scripts           [Days 11-12, 4 GPU-hours]
              +-- Assemble 60K handwriting set      [Days 14-15]
                    +-- [G4-1 through G4-5 TRAINING READY]
```

### 6.3 Dependency Graph Summary

The full dependency graph has seven chains with three types of inter-chain dependencies:

**Intra-chain sequential gates (cannot parallelize)**:

- E01 must precede E02 (NONE-class conventions depend on paired GT paths)
- E03 formula definition must precede E03 script implementation (by definition)
- N_A schema fix must precede E13 handwriting assembly (parser will reject N_A samples)

**Cross-chain shared resources (scheduling constraint)**:

- v3 GCS pool is consumed by E09 (shadow views), E10 (warping views), E11 (completion run),
  and E12 (orientation non-Latin views). E11 takes 100 GPU-hours and holds the GCS write lock
  during generation; E09 and E10 should complete before E11 starts or use separate v3 subsets.
- Vultr A100 VM is needed for E01 (3-4h), E05 (8h), E07 (20h), E06 (40h), E09 (6h) -- total
  approximately 77-81 GPU-hours before Modal is engaged for E11 and training runs.
- DIQA-5000 is re-labeled in E05 (RQ V2) and also referenced in E08 (VLM V2). These can run
  concurrently since they produce separate output fields.

**Parallel opportunities (can execute simultaneously)**:

- E01 (shadow labeling) || E03 Part 1 (warping formula design)
- E05 (RQ V2 code) || E07 (IQA sub-command) || E12 (orientation rebuild)
- E09 (v3 shadow views) || E10 (v3 warping write-back)
- E13 (handwriting enrichments for KHATT, CASIA, IIIT-HW -- three independent runs)
- E17 (capture_cls -- no dependencies -- execute immediately)

### 6.4 Phase-Aligned Timeline

#### Phase 0 -- Days 1-2: Schema Fixes (Zero GPU Cost)

| Day | Action | ID | Output | Heads Unblocked |
|-----|--------|----|--------|-----------------|
| 1 | Execute `prepare_multitask_datasets.py source` (dry-run passes -- just run it) | E17 | 39,893 capture_cls records | G5-1 |
| 1 | Fix N_A sentinel in handwriting presence schema | Schema | Schema updated | G4-1 gate cleared |
| 1 | Define ILLEGIBLE void bucket [0.0-0.05] | Schema | Convention documented | G4-2 gate cleared |
| 1 | Rename code_reg to code_cls across all references | Schema | Naming consistent | G5-4 |
| 2 | Execute `label_shadow_severity.py` (sd7k + wsrd, spot-check 50 first) | E01 | approximately 11,700 L2 severity labels | G5-2 data start |
| 2 | Define WARP-G02 formula; begin 50-sample calibration run on doc3d | E03 P1 | Formula documented | G5-3 design gate |
| 2 | Add severity write-back to `generate_v3_shadow_view.py` (1-line fix) | E09 prep | Script fixed | G5-2 synthetic ready |
| 2 | Document skew synthetic cap decision (accept 79% or add natural sources) | Schema | Decision recorded | MNV4-H2 metadata |

**Execution note**: E17 is the highest-ROI action in the entire catalog and has zero blocking
dependencies. It should be the first command executed on Day 1.

#### Phase 1 -- Days 3-7: Quick Wins and Critical Path Starts

| Days | Action | ID | GPU-hours | Output | Heads |
|------|--------|----|:---------:|--------|-------|
| 3-4 | NONE-class shadow construction | E02 | <1 | approximately 7K NONE-class records | G5-2 |
| 3-4 | Execute `generate_v3_shadow_view.py` (8K, 4 types) | E09 | approximately 6 | 8K shadow images + L2 sidecars | G5-2 |
| 4-5 | Implement `label_warping_severity.py` Part 1 (doc3d mesh parser) | E03 | 0 | Script ready for doc3d run | G5-3 |
| 4-5 | Execute orientation rebuild (DocLayNet + RVL-CDIP + v3 non-Latin) | E12 | approximately 8 | 50K orientation images | MNV4-H1, G3 |
| 5-6 | Begin IQA sub-command implementation | E07 | 0 | Sub-command skeleton | G1-1 to G1-6 |
| 6-7 | Run `label_warping_severity.py` on 102K doc3d images | E03 | approximately 4 | 102K warping_severity labels | G5-3 |
| 7 | Shadow training set assembly (`prepare_multitask_datasets.py shadow`) | Chain A | <1 | 15K shadow training manifest | **G5-2 READY** |

**Critical path note**: The warping chain (E03) has the longest lead time of any assembly chain.
Parallel execution of E03 formula design alongside E01 shadow execution on Day 2 is the most
important scheduling decision in Phase 0.

#### Phase 2 -- Days 8-15: Core Assembly

| Days | Action | ID | GPU-hours | Output | Heads |
|------|--------|----|:---------:|--------|-------|
| 8-9 | NONE-class warping construction + v3 warping severity write-back | E04, E10 | approximately 4 | 7K NONE + 5K synthetic warping | G5-3 |
| 8-9 | Warping training set assembly | Chain B | <1 | 20K warping manifest | **G5-3 READY** |
| 9-10 | Execute IQA sub-command (100K synthetic generation) | E07 | approximately 20 | 100K IQA images, 6 labels each | G1-1 to G1-5 |
| 10-11 | RQ V2 code upgrade (Sauvola + projection profiles) | E05 | 0 | Updated `resolution_quality.py` | MNV4-H3, G5-5 |
| 11-12 | Run RQ V2 labeling on 3 datasets (DIQA-5000, OHR-Bench, RealDAE) | E05 | approximately 8 | approximately 15.2K resolution labels | MNV4-H3, G5-5 |
| 11-12 | Run KHATT + CASIA-HWDB2 + IIIT-HW-Hindi integration scripts | E13 | approximately 6 | L2 metadata for 3 HW datasets | G4-1 to G4-5 |
| 12-13 | Multi-column skew quality gate (cross-detector agreement) | E19 | approximately 2 | Cleaned 90K skew dataset | MNV4-H2, G3 |
| 13-14 | Script dataset assembly (`prepare_multitask_datasets.py script`) | Chain E | <1 | Script manifest (190K v3 + MDIW13) | G2 |
| 14-15 | Handwriting training set assembly (stratified, 60K) | E13 | <1 | 60K handwriting manifest | **G4-1 to G4-5 READY** |
| 15 | ILP optimizer run (PuLP, 25 sources x 10 datasets) | E18 | <1 CPU | Optimal allocation matrix | All 22 heads |

**Milestone check (Day 15)**: By end of Phase 2, the following datasets should be assembled
and training-manifest-ready: capture_cls (G5-1), shadow (G5-2), warping (G5-3), IQA G1-1
through G1-5, orientation (MNV4-H1, G3), and handwriting (G4-1 through G4-5). Remaining
not-ready: G1-6 overall_quality (VLM gate), G2 script (v3 completion), MNV4-H3/G5-5
resolution (teacher training pipeline). MNV4-H1 and MNV4-H2 are ready for immediate training;
SigLIP 2 warmup can begin with the assembled G1, G2, G3, G5 datasets.

#### Phase 3 -- Days 16-25: Advanced Enhancements

| Days | Action | ID | GPU-hours | Output | Heads |
|------|--------|----|:---------:|--------|-------|
| 16-18 | v3 completion run (fix generator bug, resume 160K remaining) | E11 | approximately 100 | v3 at 350K images | G2, G1 pool |
| 16-17 | VLM IQA re-labeling V2 (validate 30-50 images first; gate: SRCC > 0.60) | E08 | approximately 5 + $20-30 API | 2-5K VLM-labeled overall_quality | G1-6 |
| 18-19 | Book gutter shadow augmentation (page_curl + gutter shadow overlay) | E15 | approximately 1 | 1K compound shadow+warp images | G5-2, G5-3 |
| 18-19 | ADF curl augmentation (Augraphy transverse curl on DocLayNet) | E16 | approximately 1 | 300-500 ADF curl images | G5-3 |
| 20-22 | Compound degradation augmentation (5-type stacking on doc3d test) | E14 | approximately 3 | 500 compound OOD images | G1-1 to G1-6, G5-2, G5-3 |
| 22-24 | Synth-250K resolution teacher dataset generation | E06 | approximately 40 | 250K images, Tier 0 RQ labels | MNV4-H3, G5-5 |
| 24-25 | Resolution teacher model training (MobileNetV4 on 250K synth) | E06 | approximately 30 | Teacher checkpoint | MNV4-H3, G5-5 |

**VLM V2 gate decision (Day 17)**: If SRCC <= 0.60 on the 30-50-image validation batch,
the VLM path should be abandoned for regression and the overall_quality head should proceed
with synthetic Tier 0 composite labels only (weighted average of G1-1 through G1-5 parameters).
This avoids a 3-day effort sink on a path with uncertain outcome.

#### Phase 4 -- Post-Training: Pseudo-Labeling and Active Learning

| Milestone | Action | ID | Prerequisites | Duration |
|-----------|--------|----|:-------------:|---------|
| Pseudo-label real resolution data | Teacher inference on DIQA-5000 + OHR-Bench + RealDAE with MC Dropout | E06 Phase 4 | Teacher checkpoint | 1-2 days |
| Resolution student training | Student on 250K synth + approximately 15K real (soft labels, KL-div loss) | E06 Phase 4 | Pseudo-labels | 3-5 days |
| First SigLIP 2 evaluation | Per-head validation loss; failure cluster identification by diversity dimension | E20 | First training run | 1-2 days |
| Active learning analysis | Flag heads val_loss > 2x median; dimensions error > 1.5x average | E20 | Evaluation complete | 1 day |
| Targeted re-sampling | Targeted synthetic or re-weighted real samples for failing (dimension, head) pairs | E20 | Analysis | 3-5 days/iteration |
| Model recalibration | Retrain with augmented datasets; re-evaluate | E20 | Samples generated | 5-10 days |

### 6.5 Consensus-Validated Go/No-Go Timeline

The following table integrates the Tier Feasibility Consensus (Round 2) recommendations with
the phase-aligned timeline above:

| Horizon | Heads Ready for Training | Consensus Verdict |
|---------|:------------------------:|:-----------------:|
| 4 weeks (end of Phase 1) | MNV4-H1, MNV4-H2 (immediately) + G5-1 capture, G5-2 shadow | GO for MNV4 bootstrap only; 4/4 consensus |
| 8 weeks (end of Phase 2) | MNV4-H1, MNV4-H2, G1-1 to G1-5, G2, G3, G5-1, G5-2, G5-3, G4-1 to G4-5 | GO for T4+T6 core: IQA, Geometry, Script, Page Attrs; 3/4 consensus |
| 12 weeks (end of Phase 3) | All 22 heads with T5 handwriting integrated | GO for T4+T6 expanded + T5 handwriting; 3/4 consensus |

The resolved hybrid strategy -- T4+T6 now with parallel T5 acquisition -- captures 80% of the
quality ceiling of the full T5+T6 strategy at approximately 50% of the cost and timeline.

### 6.6 Performance Expectations

Based on the four-model consensus (Round 1), the following calibrated estimates apply:

| Scenario | IQA MAE Impact | IQA SRCC | Skew MAE | Script Accuracy |
|----------|:--------------:|:--------:|:--------:|:---------------:|
| Full corpus (25K+ real + 100K pseudo) | Baseline | 0.82-0.88 | 0.837 (current) | 80-92% (frozen backbone) |
| 50% minimum samples (16.3K vs. 25K+100K) | +25-45% MAE increase | 0.60-0.75 | -- | 65-84% (full fine-tune) |
| VLM labels at SRCC 0.53 used for regression | Model ceiling 0.45-0.60 | Not usable | -- | -- |
| Synthetic-only geometry (no natural injection) | -- | -- | +0.3-0.5 MAE | -- |
| Frozen backbone script classifier | -- | -- | -- | 90%+ (50-100 samples/class) |

**Key planning constraint from consensus**: The IQA heads (G1-1 through G1-6) require a
minimum of 15,000-25,000 real annotated samples for production deployment. The E07 synthetic
pipeline (100K images) is the primary path to this target, but the synthetic images are
Tier 0 only on augmentation parameters -- not on perceptual quality matching to real-world
degradation. Real-world calibration via E05 (RQ V2) and E08 (VLM V2, if gate passes) remains
necessary for G1-6 overall_quality.

### 6.7 Execution Checklist -- Day 1 Actions

The following three actions have zero dependencies and should execute immediately:

1. **`uv run python scripts/prepare_multitask_datasets.py source --l2-metadata-dir /mnt/e/image_detection/metadata_registry/json/ --output-dir [target]`**
   -- ROI 3.96; G5-1 capture_cls unblocked; 0.5 days.

2. **Fix N_A sentinel in L2 schema** -- parser edit; G4-1 handwriting gate cleared; 0.5 days.

3. **Fix ILLEGIBLE void convention** -- bucket definition [0.0-0.05]; G4-2 legibility gate
   cleared; 1 day.

These three actions deliver more unblocked head-days per engineering hour than any other
action in the catalog.

---

## Section 7: Multi-Model Consensus Validation

Four consensus rounds were conducted with a panel of four AI models. Each round addressed a specific decision domain. Models were assigned adversarial stances (FOR, AGAINST, NEUTRAL) to stress-test recommendations and surface disagreements.

**Panel composition (all 4 rounds):**

| Model | Role | Mean Confidence |
|-------|------|:---------------:|
| google/gemini-2.5-pro | FOR T4+T6 (Rounds 2, 4); NEUTRAL (Rounds 1, 3) | 8.5/10 |
| google/gemini-3-pro-preview | AGAINST rushing (Rounds 2, 4); NEUTRAL (Rounds 1, 3) | 9.0/10 |
| deepseek/deepseek-r1-0528 | NEUTRAL quantitative (all rounds) | 8.25/10 |
| x-ai/grok-4 | NEUTRAL commercial ROI (all rounds) | 7.75/10 |

**Overall mean confidence: 8.5/10** across all 4 models and all 4 rounds.

### 7.1 Round 1: Performance Delta Calibration

**Objective**: Calibrate expected performance degradation when training with incomplete data, low-quality labels, or class imbalance.

**Six calibration topics evaluated:**

1. IQA regression at 50% minimum samples (16.3K vs. 25K+100K target)
2. VLM labels at SRCC 0.53 for regression training
3. Script classifier with 8.6x class imbalance
4. Synthetic vs. annotated labels for geometric tasks
5. Phased training with zero-shot heads
6. Minimum viable training corpus size

**Unanimous agreements (4/4):**

- VLM labels at SRCC 0.53 are REJECTED for regression training. Ceiling SRCC achievable by a model trained on such labels is 0.45-0.60. The consensus gate threshold is SRCC >= 0.65.
- Synthetic labels are SUPERIOR to human-annotated labels for geometric tasks (orientation, skew). Tier-0 labels are mathematically exact; human labels would degrade accuracy.
- 16.3K hard labels alone are insufficient for production deployment of IQA regression heads.

**Key disagreements:**

- Degradation magnitude: 2x range between Grok 4 (+10-20% MAE) and Gemini 3 Pro/DeepSeek R1 (+40-60% MAE). Resolution: Use Gemini 2.5 Pro median (+25-40%) as planning estimate.
- VLM gate threshold: 0.60 (Grok 4, DeepSeek) vs. 0.70 (both Gemini). Resolution: 0.65 compromise with classification fallback below 0.65.
- Feature drift in phased training: Only Gemini 3 Pro flags as critical risk. Resolution: Freeze backbone during warmup (5 epochs) as precaution.

**Actionable outcomes:**

- MNV4 H1+H2: Train immediately (UNANIMOUS GO)
- Script classifier: READY with frozen backbone approach (50-100 samples/class sufficient)
- IQA data: Critical path -- prioritize reaching 25K real + pseudo-labeling pipeline
- SigLIP warmup: Proceed with frozen backbone, 3+ groups, gate at SRCC > 0.65

### 7.2 Round 2: Tier Feasibility Assessment

**Objective**: Determine which data tier strategy maximizes training readiness within cost and timeline constraints.

**Stances**: Gemini 2.5 Pro (FOR T4+T6), Gemini 3 Pro Preview (AGAINST T4+T6), DeepSeek R1 (NEUTRAL), Grok 4 (NEUTRAL go/no-go focus).

**Unanimous agreements (4/4):**

1. T2/T3 are dominated dead ends -- neither unblocks meaningful heads beyond MNV4-H1/H2
2. MNV4 H1+H2 immediate GO regardless of tier strategy
3. No tier achieves full 22-head production in 12 weeks
4. Handwriting (G4) is the highest-risk group across all strategies

**Performance ceiling consensus:**

| Strategy | Consensus Ceiling |
|----------|:-----------------:|
| T2 (MIT) | approximately 25% |
| T3 (NC) | approximately 35% |
| T3+T6 | approximately 55% |
| T4+T6 | approximately 75% |
| T5+T6 | approximately 85% |

**Critical dissent (Gemini 3 Pro Preview, 1/4):**

- "False Summit" argument: T4+T6 high scores are Latin-biased; model will fail on non-Latin documents. T5-Lite proposed: prioritize CASIA (Chinese) + IIIT (Hindi) immediately.
- Rebuttal: Valid for G4 handwriting heads (Latin-only without KHATT/CASIA/IIIT). Invalid for G1 IQA heads (blur/noise/contrast are script-agnostic physical properties). Invalid for G5 page attributes (shadow/warping/capture are physical, not script-dependent).

**Actionable outcome**: Resolved hybrid strategy -- T4+T6 NOW + parallel T5 acquisition. This captures 80% of quality ceiling at approximately 50% of cost.

### 7.3 Round 3: Enhancement Plausibility

**Objective**: Validate the feasibility and expected yield of the top 8 computational enhancements.

**Final viability matrix:**

| Enhancement | Consensus Score | Verdict |
|-------------|:---------------:|---------|
| E11 v3 completion (190K to 350K) | 9.5/10 | UNANIMOUS TOP PRIORITY |
| E01 shadow severity (luminance delta) | 8.75/10 | UNANIMOUS STRONG |
| E05 RQ V2 (Sauvola+projection) | 8.0/10 | STRONG GO |
| E07 IQA synthetic (blur/noise/contrast) | 7.5/10 | GO (with domain gap mitigation) |
| E03 warping severity (Doc3D mesh) | 6.75/10 | CONDITIONAL |
| E13 handwriting harmonization | 5.25/10 | BLOCKED (legibility) |
| E08 VLM IQA v2.0 | 5.0/10 | CONDITIONAL (pivot to blind IQA) |
| E14 compound distortion (500 images) | 3.75/10 | SCALE UP 20x |

**Critical discovery -- E03 warping formula flaw:**

Gemini 3 Pro Preview identified that raw `std(Z_grid)` from Doc3D mesh is INVALID as warping severity metric. A flat page tilted 45 degrees has high Z-std but zero warping. The consensus resolution requires plane detrending: `std(Z - plane_fit(Z))` to isolate non-rigid deformation from rigid pose variation. Without this fix, E03 viability drops from 8/10 to 4/10.

**Critical pivot -- E08 VLM to blind IQA models:**

All four models agreed that VLM (Claude/GPT vision) fundamentally lacks frequency-domain analysis needed for IQA regression. VLM SRCC 0.53 cannot reach 0.65 with prompt engineering alone. Recommended pivot: replace VLM with specialized blind IQA models (LIQE, MUSIQ, PaQ-2-PiQ) with expected SRCC 0.65-0.80 on document images.

**Resolved disagreements:**

- E03 formula: Plane detrending mandatory (Gemini 3 Pro identified flaw; all agree after discussion)
- E07 domain gap: 30-50% real mix + style-transfer optional (compromise)
- E08 VLM viability: Pivot to blind IQA; keep VLM as fallback only
- E14 minimum scale: 10K target, 5K minimum (compromise between 5K and 20K positions)

### 7.4 Round 4: Final Recommendation

**Objective**: Synthesize all prior rounds into a final go/no-go recommendation with phased implementation strategy.

**Stances**: Gemini 2.5 Pro (FOR T4+T6), Gemini 3 Pro Preview (AGAINST rushing), DeepSeek R1 (NEUTRAL quantitative), Grok 4 (NEUTRAL commercial ROI).

**Unanimous agreements (4/4, 6 items):**

1. Fix 3 architectural defects FIRST -- highest ROI action, zero-cost prerequisite
2. Defer G4 handwriting heads from MVP -- readiness 38-52 insufficient
3. Legal/licensing resolution is P0 -- sd7k/wsrd unknown license, deployment model decision
4. T4+T6 is the correct foundation tier -- dominates T2/T3/T3+T6 on cost-adjusted ROI
5. No technical fatal flaw in T4+T6 -- strategy is sound
6. 12-week GO with approximately 75% readiness (G4 disabled) is achievable

**Strong majority (3/4):**

1. Phase 1 MNV4 on T4, Phase 2 SigLIP on T4+T6
2. 8-week CONDITIONAL GO for SigLIP core heads
3. E11 v3 completion is highest-ROI enhancement (after arch fixes) -- 9.5/10 viability
4. Descope MVP to approximately 16 heads (exclude G4 5 heads + G3-2 skew_post)

**Critical dissent (Gemini 3 Pro Preview, 1/4):**

1. CC-BY-SA-4.0 may be FATAL for distributed deployment. If SaaS-only, SA clause is irrelevant (model weights never distributed). If distributed (on-prem, edge, mobile SDK), SA clause requires open-sourcing weights. This is a P0 BUSINESS DECISION that must be resolved before finalizing data strategy.
2. Validate on T2 clean data before scaling to T4+T6 -- adds 2-3 weeks but reduces risk. REJECTED: T4+T6 is a superset of T2; architecture defects are code fixes, not data-dependent.
3. 8-week SigLIP is NO-GO -- only MNV4 GO at 8 weeks. PARTIALLY ADOPTED: Treat 8 weeks as conditional gate, not guaranteed GO.

### 7.5 Cross-Round Synthesis

**Findings that strengthened across rounds:**

1. T4+T6 recommendation grew from "recommended foundation" (Round 2, 3/4) to "correct foundation tier" (Round 4, 4/4 unanimous). No model reversed its position.
2. VLM rejection held firm across Rounds 1, 3, and 4. The pivot to blind IQA models (Round 3) was endorsed in Round 4 as the preferred alternative.
3. G4 handwriting deferral: Identified as highest-risk in Round 2, confirmed as "defer from MVP" in Round 4. No model argued for G4 inclusion in Release 1.

**Findings that evolved across rounds:**

1. Warping formula: Round 2 assumed `std(Z_grid)` was valid. Round 3 discovered the plane detrending requirement. Round 4 incorporated the fix into the Phase 1 timeline.
2. SigLIP 8-week timeline: Round 2 said "GO core" (3/4). Round 4 downgraded to "CONDITIONAL GO" after Gemini 3 Pro's dissent about prerequisite completion risk.
3. E08 VLM IQA: Round 1 set the 0.65 gate. Round 3 identified the fundamental limitation. Round 4 adopted the blind IQA pivot as the primary path.

**Persistent disagreements (unresolved):**

1. CC-BY-SA-4.0 deployment compatibility: Gemini 3 Pro maintains this is potentially fatal for distributed deployment. Other models acknowledge the concern but classify it as a legal question, not a technical blocker. Resolution: Adopted as P0 business decision; technical work proceeds in parallel.
2. T2 validation step: Gemini 3 Pro recommends a 2-3 week T2-first validation. Other models reject as unnecessary given T4+T6 is a strict superset. Resolution: Rejected, but small smoke test after defect fixes is recommended.

---

## Section 8: Final Decision Matrix

### 8.1 Go/No-Go Verdicts by Horizon

| Horizon | MNV4 (3 heads) | SigLIP Core (11 heads) | SigLIP Expanded (16 heads) | G4 Handwriting (5 heads) |
|---------|-----------------|------------------------|----------------------------|--------------------------|
| 4 weeks | CONDITIONAL GO | NO-GO | NO-GO | NO-GO |
| 8 weeks | GO | CONDITIONAL GO | NO-GO | NO-GO |
| 12 weeks | GO | GO | CONDITIONAL GO | NO-GO (Release 2) |
| 16+ weeks | GO | GO | GO | CONDITIONAL GO (T5 data) |

**Conditional GO criteria:**

- **4-week MNV4**: All 3 architectural defects fixed + legal deployment model decided (SaaS vs. distributed)
- **8-week SigLIP Core**: E11 (v3 completion) + E01 (shadow labeling) complete + legal clear + 7 or more heads at val SRCC > 0.65
- **12-week SigLIP Expanded**: E03 (warping with plane detrending) + E05 (RQ V2) complete + G3 heads integrated + 14 or more heads at quality gate
- **16-week G4 Handwriting**: T5 handwriting data acquired (KHATT, CASIA, IIIT) + ILLEGIBLE class synthesized via degradation augmentation

### 8.2 Recommended Phasing Strategy

**Phase 0: Prerequisites (Weeks 1-2)**

- Fix 3 architectural defects (1-2 days engineering)
- Resolve deployment model decision (SaaS vs. distributed) -- P0 BUSINESS
- Initiate legal review of sd7k/wsrd licenses
- Initiate legal review of TOU datasets (DIQA-5000, OHR-Bench, RVL-CDIP, IAM)

**Phase 1: MNV4 Bootstrap (Weeks 2-4)**

- Train MNV4-Conv-S with 3 heads on T4 data
- Orientation (50K), Skew (90K), Resolution Quality (15K after E05)
- Validate: orientation acc > 95%, skew MAE < 1.0, RQ SRCC > 0.70

**Phase 2: SigLIP Warmup (Weeks 4-8)**

- Execute E11 (v3 completion 350K) and E01 (shadow labeling 12K)
- Train SigLIP core heads: G1 IQA (6) + G2 Script (1) + G5 Page Attrs (4) = 11 heads
- Freeze backbone during warmup (5 epochs) per Consensus Round 1 recommendation
- Validate: IQA SRCC > 0.65, script acc > 80%, shadow SRCC > 0.65

**Phase 3: SigLIP Expansion (Weeks 8-12)**

- Integrate G3 geometry heads (orientation_post, skew_post)
- Execute E03 (warping with plane detrending) and E05 (RQ V2)
- Add remaining near-ready G5 heads
- Validate all active heads stable (loss variance < 0.1)

**Phase 4: Release 2 Preparation (Weeks 12+)**

- Integrate T5 handwriting data (KHATT, CASIA, IIIT)
- Synthesize ILLEGIBLE class via degradation augmentation
- Train G4 handwriting heads
- Teacher pseudo-labeling on production data

**Parallel Track (Weeks 1-12)**

- T5 data acquisition: KHATT (Arabic), CASIA-HWDB2 (Chinese), IIIT-HW-Hindi (Devanagari)
- Legal review and resolution
- OOD corpus expansion (2,985 to 12,000 images)

### 8.3 Head Deferral Decisions

**Release 1 scope: 16 heads**

| Head | Group | T4+T6 Score | Status |
|------|-------|:-----------:|--------|
| MNV4-H1 orientation_cls | MNV4 | 68 | INCLUDED |
| MNV4-H2 skew_reg | MNV4 | 52 | INCLUDED |
| MNV4-H3 resolution_quality_reg | MNV4 | 68 | INCLUDED |
| SIG-G1-1 blur_score | G1 | 82 | INCLUDED |
| SIG-G1-2 noise_score | G1 | 82 | INCLUDED |
| SIG-G1-3 contrast_score | G1 | 82 | INCLUDED |
| SIG-G1-4 skew_score | G1 | 74 | INCLUDED |
| SIG-G1-5 compression_score | G1 | 82 | INCLUDED |
| SIG-G1-6 overall_quality | G1 | 76 | INCLUDED |
| SIG-G2-1 script_cls | G2 | 72 | INCLUDED |
| SIG-G3-1 orientation_cls (post) | G3 | 62 | INCLUDED |
| SIG-G5-1 capture_cls | G5 | 64 | INCLUDED |
| SIG-G5-2 shadow_reg | G5 | 75 | INCLUDED |
| SIG-G5-3 warping_reg | G5 | 68 | INCLUDED |
| SIG-G5-4 code_cls | G5 | 71 | INCLUDED |
| SIG-G5-5 resolution_quality_reg | G5 | 66 | INCLUDED |

**Release 2 deferred: 6 heads**

| Head | Group | T4+T6 Score | Deferral Reason |
|------|-------|:-----------:|-----------------|
| SIG-G3-2 skew_reg (post, +/-2 deg) | G3 | 40 | +/-2 degree dataset does not exist; must be built from scratch (T5 action) |
| SIG-G4-1 presence_cls | G4 | 52 | N_A sentinel fix required + multi-script harmonization incomplete |
| SIG-G4-2 legibility_cls | G4 | 32 | ILLEGIBLE void -- 0 negative examples; IAA ceiling below target |
| SIG-G4-3 content_type_cls | G4 | 50 | MIXED_TYPED_HW class -- 0 natural examples across all corpora |
| SIG-G4-4 presence_reg | G4 | 50 | Bimodal distribution gap (mid-range 0.2-0.7 near-empty) |
| SIG-G4-5 legibility_reg | G4 | 38 | IAA ceiling (0.60-0.65) below Pearson r >= 0.80 target; target revision mandatory |

### 8.4 Risk Registry

| # | Risk | Probability | Impact | Mitigation | Owner |
|---|------|:-----------:|:------:|------------|-------|
| R1 | CC-BY-SA-4.0 incompatible with deployment model | Medium | CRITICAL | Legal review by week 2; maintain MIT-only fallback path (S1 scenario). If distributed deployment required, exclude kuzushiji/hiertext/midv2020 and accept reduced handwriting/script coverage. | Legal / Business |
| R2 | sd7k/wsrd license unresolvable (authors unresponsive) | Medium | HIGH | Replace with synthetic shadow from v3 (8K images) + doc3d paired samples. Reduces camera-shadow domain diversity but meets 15K volume target. Synthetic-only shadow head scores approximately 60 vs. 75 with real data. | Data Engineering |
| R3 | v3 generator bug harder to fix than expected | Low | HIGH | Cap at 190K images; add MDIW13 (753 real) + MLT-19 (20K, TOU) as backup sources for script head. Script classifier still viable at 190K with frozen backbone approach. | ML Engineering |
| R4 | SigLIP 8-week training convergence failure | Medium | MEDIUM | Reduce active heads from 11 to 8 (drop lowest-scoring heads); extend timeline to 12 weeks. Kendall uncertainty weighting isolates problematic heads automatically. | ML Engineering |
| R5 | G4 handwriting data acquisition delays | High | LOW (deferred) | Release 2 planning absorbs delay. G4 heads are already deferred; any acquisition delay shifts Release 2 timeline without affecting Release 1. | Data Engineering |

### 8.5 Critical Dissent Record

Two substantive dissents from Gemini 3 Pro Preview are recorded for decision-maker review. Both were evaluated by the full panel and partially adopted.

**Dissent 1: CC-BY-SA-4.0 Deployment Compatibility (ADOPTED as P0 business decision)**

- **Claim**: If the intended deployment model includes distributed weights (on-prem, edge, mobile SDK), the CC-BY-SA-4.0 clause may require open-sourcing model weights. Under conservative legal posture (training produces derivative work), model weights inherit the SA obligation.
- **Counter-argument**: CC-BY-SA applies to TRAINING DATA, not necessarily to model weights. Legal gray area; many foundation models (CLIP, DINOv2) were trained on CC-BY-SA data and released under Apache/MIT without enforcement.
- **Resolution**: ADOPTED. The deployment model decision is elevated to P0 business priority. Technical data preparation work proceeds in parallel -- the CC-BY-SA question affects model card and release strategy, not training methodology. If SaaS-only deployment is chosen, the SA clause is irrelevant.
- **Impact on recommendation**: None for technical phasing. Critical for legal and business planning.

**Dissent 2: T2-First Validation Step (REJECTED with compromise)**

- **Claim**: Validate architecture fixes and basic training pipeline on T2 (MIT-clean) data before scaling to T4+T6. This adds 2-3 weeks but reduces risk of learning on noisy or legally questionable data.
- **Counter-argument**: T4+T6 is a strict superset of T2 data. Architecture defects are code fixes that can be validated with a 100-image smoke test, not a full T2 training cycle. The 2-3 week delay is not justified.
- **Resolution**: REJECTED as a formal phase. Compromise: Run a small smoke test (100-500 images) after fixing the three architectural defects to verify masked loss and BCE loss function correctly. This takes hours, not weeks.
- **Impact on recommendation**: Minor -- adds a half-day validation step to Phase 0.

---

## Appendix A: Methodology

### A.1 Analysis Pipeline

The strategic analysis was conducted in five phases:

1. **Phase 0 -- Defect Identification**: Automated codebase audit identified 3 architectural defects across schema definitions, head registries, and training scripts. Defects were classified by severity (CRITICAL, HIGH, MEDIUM) and effort to resolve.

2. **Phase 1-3 -- Parallel Analyst Subagents**: Three specialized analyst subagents operated in parallel:
   - **Analyst-A (Scoring)**: Constructed the 22-head x 5-tier scoring matrix using the D1-D6 rubric across all heads and tiers. Source data: HAR_SYNTHESIS.md (22 individual head adequacy reports), UNIFIED_TRAINING_CORPUS.md, CORPUS_OOD_REVIEW_REPORT.md.
   - **Analyst-B (Licensing)**: Assessed license compatibility for all 62 datasets under S1/S2a/S3 scenarios. Source data: individual dataset documentation files, LICENSE files, paper appendices.
   - **Analyst-C (Enhancements)**: Catalogued 20 computational enhancements with ROI scoring, dependency graphs, and per-head coverage matrices. Source data: existing scripts, DATASET_DIVERSITY_REQUIREMENTS.md, TRAINING_OPTIMIZATION_PLAN.md.

3. **Phase 4 -- Consensus Rounds**: Four sequential consensus rounds with a 4-model panel (Gemini 2.5 Pro, Gemini 3 Pro Preview, DeepSeek R1 0528, Grok 4). Adversarial stances were assigned to stress-test recommendations.

4. **Phase 5 -- Report Assembly**: Analyst outputs and consensus checkpoints were assembled into this document by two writer subagents (Writer-D for Sections 1-3, Writer-E for Sections 4-6) with fresh synthesis for the Executive Summary, Section 7, Section 8, and Appendices.

### A.2 Scoring Methodology

**D1-D6 Dimensions (10 points each, 60 maximum):**

| Dimension | What It Measures | Scoring |
|-----------|-----------------|---------|
| D1 (Sample Count) | Images assembled vs. minimum target | Prorated: (actual / target) x 10, capped at 10 |
| D2 (Synthetic Cap) | Synthetic percentage vs. stated cap | 10 if compliant; 0-7 if violation (proportional to overage) |
| D3 (Label Quality) | Percentage of samples at confidence >= 0.6 | 10 if > 80%; 0-5 if VLM bottleneck or SRCC gate fails |
| D4 (Diversity) | Dimensions represented out of 14 | 10 if >= 7; 6-8 if 5-6; 0-4 if < 5 |
| D5 (Wild Conditions) | Section 8 requirements met | Prorated per applicable requirement |
| D6 (Cross-Head Conflicts) | Unresolved conflicts between heads | 10 minus 2-5 per conflict |

**P0 Bonus (40 points maximum):**

- Awarded when zero P0 gaps are present for the head
- Partially awarded (0-30) when P0 gaps exist but are resolvable at the current tier
- Zero when P0 gaps are structural (require T5 acquisition)

**Total: D1 + D2 + D3 + D4 + D5 + D6 + P0 Bonus = 100 maximum**

### A.3 Consensus Protocol

- **Panel size**: 4 models (minimum for adversarial stance coverage)
- **Stance assignment**: 1 FOR, 1 AGAINST, 2 NEUTRAL (Rounds 2, 4); 4 NEUTRAL (Rounds 1, 3)
- **Agreement thresholds**: Unanimous (4/4) = adopted without caveat; Strong majority (3/4) = adopted with dissent recorded; Split (2/2) = escalated to synthesis resolution
- **Confidence scoring**: Each model provides 1-10 confidence; mean confidence reported per round
- **Dissent recording**: All 1/4 dissents are recorded verbatim with rebuttals and resolutions

### A.4 Label Quality Tiers

| Tier | Name | Definition | Examples |
|------|------|-----------|---------|
| tier_0 | EXACT | Label is mathematically derived from the generation process; zero annotation noise | Rotation angle from synthetic rotation; JPEG quality parameter; Augraphy blur kernel size |
| tier_1 | ANNOTATED | Human annotation with documented IAA | DIQA-5000 MOS scores (crowdsourced, 5-point scale); KHATT legibility ratings |
| tier_2 | MODEL | Model-generated labels with measured correlation to ground truth | VLM IQA scores (SRCC measured against MOS); Hough-derived skew angles (confidence gated) |
| tier_3 | HEURISTIC | Rule-based labels with approximate accuracy | PaddleOCR confidence as resolution proxy; Unicode range as script label |
| tier_4 | PSEUDO | Inherited or inferred labels with low confidence | Dataset-level domain label applied per-image; DPI range as resolution tier |

---

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **HAR** | Head Adequacy Review -- per-head assessment of training data readiness using a domain-specific rubric |
| **D1-D6** | Six scoring dimensions: Sample Count, Synthetic Cap, Label Quality, Diversity, Wild Conditions, Cross-Head Conflicts |
| **T2-T6** | Data tier strategies: T2 (MIT commercial), T3 (NC/SA expanded), T4 (Enriched Current), T5 (Targeted Collection), T6 (Computational Enhancement overlay) |
| **CE / E01-E20** | Computational Enhancement identifiers. E01 through E20 denote specific enhancement actions in the catalog. CE-01 through CE-13 are the T6-tier subset. |
| **P0 / P1** | Priority levels. P0 = critical blocker (must resolve before training). P1 = high priority (should resolve within current phase). |
| **MNV4** | MobileNetV4-Conv-Small -- the pre-correction gate model (approximately 4M parameters, approximately 3ms GPU inference) |
| **SigLIP** | SigLIP 2 NAFlex -- the multi-task analysis model (approximately 88M parameters, approximately 50ms GPU inference) |
| **G1-G5** | Head groups: G1 (IQA, 6 heads), G2 (Script, 1 head), G3 (Post-correction geometry, 2 heads), G4 (Handwriting, 5 heads), G5 (Page attributes, 5 heads) |
| **SRCC** | Spearman Rank Correlation Coefficient -- measures monotonic relationship between predicted and ground-truth scores |
| **MAE** | Mean Absolute Error -- average absolute difference between predicted and true values |
| **PCGrad** | Projecting Conflicting Gradients -- gradient surgery technique that projects conflicting task gradients to reduce negative transfer in multi-task learning |
| **TOU** | Terms of Use -- contractual usage restrictions on research datasets (distinct from copyright licensing) |
| **SA** | ShareAlike -- Creative Commons license condition requiring derivative works to use the same or compatible license |
| **NC** | NonCommercial -- Creative Commons license condition prohibiting commercial use |
| **OOD** | Out-of-Distribution -- data that falls outside the training distribution, used for robustness evaluation |
| **DQS** | Document Quality Score -- composite metric combining degradation severity and structural complexity for routing decisions |
| **IQA** | Image Quality Assessment -- evaluation of image degradation across blur, noise, contrast, compression, skew, and overall quality dimensions |
| **IAA** | Inter-Annotator Agreement -- measure of consistency between human annotators; sets the theoretical ceiling for model performance |
| **VLM** | Vision-Language Model -- multimodal AI model (e.g., Claude, GPT-4V) used for image annotation via prompted visual analysis |
| **Kendall weighting** | Uncertainty-based loss weighting that automatically scales per-head losses using learned task uncertainty parameters |
| **Focal loss** | Modified cross-entropy loss that down-weights well-classified examples and focuses training on hard negatives; used for class-imbalanced classification |

---

*End of document. Training Data Strategic Analysis v1.0.0, 2026-02-24.*
