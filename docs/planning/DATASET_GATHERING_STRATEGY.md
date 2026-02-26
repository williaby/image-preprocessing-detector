---
title: Dataset Gathering Strategy
schema_type: common
status: active
owner: ml-team
purpose: "Phased acquisition plan prioritizing hardest-to-get real-world data first,
  then filling gaps with synthetic generation."
tags:
- datasets
- acquisition
- planning
- training
---

# Dataset Gathering Strategy

> **Status**: Active | Planning Document
> **Version**: 1.0.0
> **Created**: 2026-02-26
> **Updated**: 2026-02-26
> **Philosophy**: Gather the most difficult real-world items first, determine their
> coverage across all required datasets, then fill remaining gaps with synthetic data.
>
> **Cross-references**:
>
> - [UNIFIED_TRAINING_CORPUS.md](../datasets/UNIFIED_TRAINING_CORPUS.md) — what the corpus must look like (§1b: unique source pool analysis)
> - [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md) — 14-dimension diversity targets
> - [CORPUS_OOD_REVIEW_REPORT.md](CORPUS_OOD_REVIEW_REPORT.md) — independent gap analysis (6/11 FAIL, 2 AT RISK)
> - [LICENSE_IMPACT_REPORT.md](LICENSE_IMPACT_REPORT.md) — license constraints per deployment scenario
> - [TRAINING_DATA_STRATEGIC_ANALYSIS.md](TRAINING_DATA_STRATEGIC_ANALYSIS.md) — tier analysis and Go/No-Go
> - [MASTER_PROJECT_PLAN.md](MASTER_PROJECT_PLAN.md) — dependency tiers and sequencing

---

## Table of Contents

1. [Guiding Principle: Hardest First](#1--guiding-principle-hardest-first)
2. [Real-World Data Difficulty Ranking](#2--real-world-data-difficulty-ranking)
3. [Cross-Head Coverage Matrix](#3--cross-head-coverage-matrix)
4. [Phase 1: Real Data Gathering](#4--phase-1-real-data-gathering)
5. [Phase 2: Coverage Assessment](#5--phase-2-coverage-assessment)
6. [Phase 3: Synthetic Fill](#6--phase-3-synthetic-fill)
7. [Phase 4: Final Gap Remediation](#7--phase-4-final-gap-remediation)
8. [Sequencing Integration with Master Plan](#8--sequencing-integration-with-master-plan)

---

## §1 — Guiding Principle: Hardest First

Real-world data is the bottleneck. Synthetic data can always be generated — scripts
exist for shadow overlays, warping transforms, code detection images, and orientation
rotations. What cannot be generated on demand are: paired ground truth datasets (sd7k,
wsrd, warpdoc), handwriting samples from specific script families (Arabic cursive, CJK,
Devanagari), human-verified labels (ILLEGIBLE class, legibility ratings), and real
scanner/camera captures with authentic artifacts (modern CIS flatbeds, ADF scanners, fax
halftone).

The strategy follows four phases:

1. **Phase 1 — Real Data Gathering**: Rank all real-world data sources by acquisition
   difficulty. Start with the hardest items first because they have the longest lead
   times (external dataset requests, legal review, GPU compute, human annotation). Run
   these tracks in parallel.

2. **Phase 2 — Coverage Assessment**: After real data is placed, audit the corpus against
   all 22 heads and 14 diversity dimensions. Calculate exactly how much synthetic data
   each head still needs.

3. **Phase 3 — Synthetic Fill**: Generate synthetic data to fill the remaining gaps using
   existing scripts and pipelines. Verify no dataset exceeds its synthetic mixing cap.

4. **Phase 4 — Final Gap Remediation**: Address any remaining gaps that neither real
   acquisition nor synthetic generation can close (VLM gate failures, acquisition
   rejections, wild condition coverage).

**Corpus context**: The unified training corpus requires **~420-440K unique images**
across 10 training dataset views serving 22 model heads (see
[UNIFIED_TRAINING_CORPUS.md §1b](../datasets/UNIFIED_TRAINING_CORPUS.md#1b--unique-source-pool-analysis)).
The per-head sizes sum to ~565K naively, but cross-dataset image sharing reduces the
actual unique image footprint by ~22%. As of 2026-02-23, the corpus has **6 of 11
acceptance criteria failing** and **2 at risk**
([CORPUS_OOD_REVIEW_REPORT.md](CORPUS_OOD_REVIEW_REPORT.md)).

---

## §2 — Real-World Data Difficulty Ranking

All real-world data sources are ranked into four difficulty tiers based on acquisition
effort, external dependencies, and lead time. The gathering sequence proceeds from
hardest (Tier S) to easiest (Tier C), so that long-lead items are initiated first.

### Tier S — Hardest (external dependencies, long lead times)

These items depend on external parties (dataset authors, legal review, human annotators)
and cannot be accelerated by compute alone.

| Rank | Data Source | Heads Served | Blocker | Lead Time | License |
|---|---|---|---|---|---|
| S1 | KHATT (Arabic cursive handwriting) | G4-1 to G4-5 (5 HW heads), G2-1 (script) | P0 prerequisite; not acquired | 4-6 weeks | Verify with KFUPM/KAU |
| S2 | CASIA-HWDB (CJK handwriting) | G4-1 to G4-5, G2-1 | P0 prerequisite; not acquired | 4-6 weeks | NLPR application form |
| S3 | IIIT-INDIC (Devanagari handwriting) | G4-1 to G4-5, G2-1 | P0 prerequisite; not acquired | 4-6 weeks | Verify with IIIT-Hyderabad |
| S4 | HKR (Russian/Cyrillic handwriting) | G4-1 to G4-5, G2-1 | P0 prerequisite; not acquired | 2-4 weeks | Kaggle/GitHub; verify commercial |
| S5 | ILLEGIBLE class samples (human annotation) | G4-2 (legibility_cls), G4-5 (legibility_reg) | 0 samples; 1,000+ needed with human-verified labels | 3-4 weeks | Derived from S1-S4 + IAM |
| S6 | Modern CIS flatbed scans (2010+) | G5-1 (capture_method_cls) | Gap 8: no known public dataset; may require physical scanning | 2-4 weeks | Self-generated |
| S7 | VLM IQA pseudo-labels (SRCC gate) | G1-1 to G1-6 (6 IQA heads) | Blocked at SRCC 0.53 vs 0.65 gate; prompt v2.0 not validated | Unknown | N/A (derived) |
| S8 | sd7k/wsrd license confirmation | G5-2 (shadow), G5-3 (warping) | Email sent to authors; treat as all-rights-reserved until confirmed | 2-4 weeks | Unconfirmed |

### Tier A — Hard (GPU compute + labeling pipelines)

These items require GPU compute time and/or labeling pipeline development, but have no
external dependencies beyond infrastructure.

| Rank | Data Source | Heads Served | Blocker | Lead Time |
|---|---|---|---|---|
| A1 | Shadow severity labels (sd7k 7,239 + wsrd 4,500) | G5-2 (shadow_reg) | GPU VM required; `label_shadow_severity.py` ready | 3-6 hours GPU |
| A2 | Warping severity labels (warpdoc + anyphotodoc6300 + wsrd + docalign12k) | G5-3 (warping_reg) | Formula defined (`clip(k * std(Z_grid), 0, 1)`); GPU VM required | 0.5d decision + 3-4d GPU |
| A3 | Resolution quality V2 labels (DIQA-5000 + OHR-Bench + RealDAE) | MNV4-H3, G5-5 (resolution_quality_reg) | Sauvola+projection V2 algorithm; PaddleOCR pipeline on Vultr A100 | 2-3 days GPU |
| A4 | ADF scanner heuristic labels (RVL-CDIP subset) | G5-1 (capture_method_cls) | Heuristic development + 100-sample manual verification required | 2-3 weeks |
| A5 | FAX artifact heuristic labels (RVL-CDIP subset) | G5-1 (capture_method_cls) | Heuristic development + 100-sample manual verification required | 2 weeks |
| A6 | doc3d warping labels (102K images, MIT) | G5-3 (warping_reg) | 3D mesh → severity conversion; GPU run | 3-4 days GPU |

### Tier B — Moderate (available data, requires assembly)

These items use publicly available datasets or existing data but require assembly work
(augmentation pipelines, generation scripts, split management).

| Rank | Data Source | Heads Served | Status | Lead Time |
|---|---|---|---|---|
| B1 | IQA compound distortion (Phase 1B sub-split) | G1-1 to G1-6 (6 IQA heads) | Augmentation pipeline on OHR-Bench/DIQA base images; 3-5K target | 3-5 days |
| B2 | SIG-G3-2 narrow-range skew dataset | G3-2 (skew post-correction) | No script exists; ~20K images at ±0.1-2° increments needed | 2-3 weeks |
| B3 | IAM handwriting (Latin) | G4-1 to G4-5 | Available; split by writer ID needed | 1-2 days |
| B4 | Book gutter shadow samples | G5-2 (shadow_reg, Gap 5) | Internet Archive CC0 book scans; ≥1,000 samples needed | 1-2 weeks |
| B5 | Symmetric document orientation samples | MNV4-H1 (orientation_cls) | ~500 pages from DocLayNet + blank forms; curation script needed | 0.5 days |
| B6 | Confound sub-dataset (resolution paradox) | MNV4-H3, G5-5 | DocLayNet PDFs rendered at 72/150/300 DPI; ~2K target | 1-2 days |

### Tier C — Easy (scripts exist, just run)

These items have ready-to-run scripts; execution is the only remaining step.

| Rank | Data Source | Heads Served | Script | Status |
|---|---|---|---|---|
| C1 | v3 completion run (190K → 350K) | 7+ heads via derived views | `generate_base_dataset_v3.py` | Bug fixed; not run |
| C2 | Orientation real component | MNV4-H1, G3-1 | `build_orientation_real_component.py` | Script ready |
| C3 | Orientation synthetic views | MNV4-H1, G3-1 | `derive_v3_orientation_view.py` | Script ready |
| C4 | Shadow synthetic views | G5-2 | `generate_v3_shadow_view.py` | Script ready |
| C5 | Warping synthetic views | G5-3 | `generate_v3_warping_view.py` | Script ready |
| C6 | Code detection generation | G5-4 (code_cls) | `generate_code_detection_dataset.py` | 8,613 dry-run |
| C7 | OOD synthetic generation | OOD evaluation | Various scripts in OOD plan | ~4,221 images ready |

---

## §3 — Cross-Head Coverage Matrix

This matrix maps each real-world source dataset to all heads it can serve, revealing
which acquisitions have the highest cross-head leverage and which are single-head
bottlenecks that must be acquired regardless.

### Source Dataset → Head Coverage

| Source Dataset | Unique Images | MNV4 H1 | MNV4 H2 | MNV4 H3 | G1 IQA | G2 Script | G3-1 | G3-2 | G4 HW | G5-1 | G5-2 | G5-3 | G5-4 | G5-5 | Heads |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DocLayNet | ~50K used | ✅ | ◐ | ✅ | ✅ | — | ✅ | — | ◖ | ✅ | — | — | ◖ | ✅ | **6-7** |
| RVL-CDIP | ~50K used | ✅ | — | — | ✅ | — | ✅ | — | — | ✅ | — | — | — | — | **3-4** |
| MDIW13 | 753 | ✅ | ✅ | ✅ | — | ✅ | ✅ | — | — | — | — | — | — | ✅ | **5** |
| MIDV500 | ~2K | — | — | ✅ | ✅ | — | — | — | — | ✅ | — | ◖ | — | ✅ | **3-4** |
| SmartDoc-QA | ~5K | — | — | ✅ | ✅ | — | — | — | — | ✅ | ◖ | ◖ | — | ✅ | **3-5** |
| OHR-Bench | 8.5K | — | — | ✅ | ✅ | — | — | — | — | — | — | — | — | ✅ | **3** |
| DIQA-5000 | 5.5K | — | — | ✅ | ✅ | — | — | — | — | — | — | — | — | ✅ | **3** |
| RealDAE | 1.2K | — | — | ✅ | ✅ | — | — | — | — | ✅ | — | — | — | ✅ | **3-4** |
| sd7k | 7.2K | — | — | — | — | — | — | — | — | — | ✅ | — | — | — | **1** |
| wsrd | 4.5K | — | — | — | — | — | — | — | — | — | ✅ | ✅ | — | — | **1-2** |
| doc3d | 102K | — | — | — | — | — | — | — | — | — | — | ✅ | — | — | **1** |
| anyphotodoc6300 | 6.3K | — | — | — | — | — | — | — | — | — | — | ✅ | — | — | **1** |
| warpdoc | 1K | — | — | — | — | — | — | — | — | — | — | ✅ | — | — | **1** |
| docalign12k | 12K | — | — | — | — | — | — | — | — | — | — | ✅ | — | — | **1** |
| KHATT | ~2K | — | — | — | — | ◐ | — | — | ✅ | — | — | — | — | — | **1-2** |
| CASIA-HWDB | ~4K | — | — | — | — | ◐ | — | — | ✅ | — | — | — | — | — | **1-2** |
| IIIT-INDIC | ~1K | — | — | — | — | ◐ | — | — | ✅ | — | — | — | — | — | **1-2** |
| HKR | ~1K | — | — | — | — | ◐ | — | — | ✅ | — | — | — | — | — | **1-2** |
| IAM | ~2K | — | — | — | — | — | — | — | ✅ | — | — | — | — | — | **1** |
| HierText | 8.3K | — | — | — | — | — | — | — | ✅ | — | — | — | — | — | **1** |

**Legend**: ✅ = primary use, ◐ = secondary/derivative use, ◖ = negatives provider, — = not applicable

### Leverage Analysis

**Highest leverage** (most heads per acquisition effort):

1. **DocLayNet** (6-7 heads): Already available locally. Every page serves orientation,
   resolution, IQA, handwriting negatives, capture method, and code negatives.
2. **MDIW13** (5 heads): Only 753 images but serves orientation, skew, resolution,
   script, and resolution quality. Already local.
3. **MIDV500 / SmartDoc-QA** (3-5 heads): Serve resolution, IQA, capture method, and
   provide shadow/warping negatives.

**Lowest leverage, highest necessity** (few heads but P0 blockers):

1. **sd7k** (1 head): Only serves shadow — but shadow has 0 real data assembled. P0 blocker.
2. **KHATT/CASIA-HWDB/IIIT-INDIC/HKR** (1-2 heads each): Only serve handwriting +
   secondary script coverage. But all four are P0 prerequisites for the handwriting group.
3. **doc3d** (1 head): Only serves warping — but provides 102K images with 3D mesh GT
   (MIT license confirmed).

**Key insight**: High-leverage datasets (DocLayNet, RVL-CDIP) are already available.
The remaining acquisition work is dominated by low-leverage, high-necessity specialized
datasets that serve 1-2 heads each. This is why the "hardest first" strategy is
critical: these specialized datasets are both the hardest to get AND the most likely to
block corpus readiness.

---

## §4 — Phase 1: Real Data Gathering

Phase 1 runs 6 parallel tracks. All tracks start simultaneously; their different lead
times mean they complete at different points over the first 6 weeks.

### Track A — Handwriting Dataset Acquisition (Weeks 1-6, Tier S)

**Goal**: Acquire the 4 P0 prerequisite handwriting datasets that are completely absent.

| Week | Action | Deliverable |
|---|---|---|
| 1 | Email KHATT dataset authors (KFUPM/KAU) — request access, confirm license | Email sent; license query logged |
| 1 | Submit CASIA-HWDB access request (NLPR/CASIA application form) | Application submitted |
| 1 | Submit IIIT-INDIC access request (IIIT-Hyderabad) | Application submitted |
| 1 | Obtain HKR from Kaggle/GitHub — verify license for commercial use | Download initiated; license documented |
| 1-2 | Cross-reference all four against [LICENSE_IMPACT_REPORT.md](LICENSE_IMPACT_REPORT.md) | License compatibility matrix updated |
| 3-6 | Receive access confirmations; download datasets; begin SHA256/pHash dedup | Datasets on local storage; dedup report |
| 3-6 | If any blocked: document in LICENSE_IMPACT_REPORT.md; activate fallback | Fallback strategy documented per blocked dataset |

**Fallback if acquisition fails**: For each blocked dataset, evaluate whether synthetic
handwriting generation (style transfer from available scripts) can provide adequate
coverage for the affected heads, or whether an alternative public dataset exists.

### Track B — GPU Labeling Pipeline (Weeks 1-3, Tier A)

**Goal**: Run severity labeling scripts on GPU VM to unblock shadow and warping datasets.

| Week | Action | Deliverable |
|---|---|---|
| 1 | Deploy Vultr A100 instance | GPU VM active |
| 1 | Run `label_shadow_severity.py` on sd7k (7,239 images) | `shadow_severity` in L2 metadata (~2h GPU) |
| 1 | Run `label_shadow_severity.py` on wsrd (4,500 images) | `shadow_severity` in L2 metadata (~1h GPU) |
| 1-2 | Confirm warping severity formula: `clip(k * std(Z_grid_normalized), 0, 1)` | Formula documented and approved |
| 2 | Run `label_warping_severity.py` on warpdoc (1,020), anyphotodoc6300 (6,306), wsrd (4,500) | `warping_severity` in L2 metadata |
| 2-3 | Run doc3d (102K) warping severity labeling (3D mesh conversion) | doc3d severity labels available |
| 2-3 | Run resolution quality V2 pipeline (Sauvola + projection) on DIQA-5000, OHR-Bench, RealDAE | V2 resolution labels for ~15K images |

**Unblocks**: Shadow view generation (C4), warping view generation (C5), DDRs #9 and #10,
`prepare_multitask_datasets.py shadow` and `warping` sub-commands.

### Track C — VLM IQA Gate (Weeks 1-4, Tier S)

**Goal**: Determine whether VLM pseudo-labeling can scale for IQA overall_quality.

| Week | Action | Gate |
|---|---|---|
| 1-2 | Revise VLM prompt to v2.0 (orientation-independent scoring) | Prompt documented |
| 2-3 | Validate v2.0 on 30-50 images; compute SRCC | **SRCC ≥ 0.60**: proceed to Gate 2 |
| 3-4 | If Gate 1 passes: scale to 2,000-5,000 images | **SRCC ≥ 0.65 at scale**: VLM path viable |
| 3-4 | If Gate 1 fails (SRCC < 0.60): enter FALLBACK PATH | Fallback: classical IQA ensemble only; reduce IQA target to 25K hard labels |

**Decision tree**:

- SRCC ≥ 0.65 at scale → Scale VLM to 100K pseudo-labels at 0.8× weight
- SRCC 0.60-0.65 at scale → Scale VLM to 50K pseudo-labels at 0.6× weight; flag for
  human spot-check of 500 samples
- SRCC < 0.60 → Abandon VLM path; train IQA heads on 25K hard labels only; accept
  reduced IQA accuracy with documented limitation

### Track D — Heuristic Labeling (Weeks 2-4, Tier A)

**Goal**: Develop and validate heuristic labels for ADF scanner and FAX artifact classes.

| Week | Action | Deliverable |
|---|---|---|
| 2 | Develop ADF scanner heuristic: edge-parallel dark bands (2-5px), systematic micro-skew (0.2-0.8°), roller dust streaks | Heuristic code in `schema_utils/` |
| 2-3 | Label 100 ADF samples from RVL-CDIP manually; verify heuristic agreement | Agreement ≥ 85% → propagate; < 85% → revise |
| 3 | If verified: propagate ADF labels to full RVL-CDIP corpus | ADF class populated (≥2,500 target) |
| 3-4 | Develop FAX halftone heuristic: screening dot pattern detection, banding artifacts | Heuristic code |
| 4 | Label 100 FAX samples manually; verify and propagate | FAX class populated (≥2,500 target) |

### Track E — Assembly from Available Data (Weeks 2-4, Tier B)

**Goal**: Assemble training data from sources already available locally or publicly.

| Week | Action | Deliverable |
|---|---|---|
| 2 | Download IAM handwriting dataset; split by writer ID (prevent writer leakage) | IAM ready; ~2K Latin handwriting images |
| 2-3 | Build IQA compound distortion augmentation pipeline on OHR-Bench/DIQA base | 3-5K compound distortion images |
| 2-3 | Curate book gutter shadow from Internet Archive CC0 book scans | ≥1,000 book gutter shadow samples |
| 3 | Build SIG-G3-2 narrow-range skew generation script (±0.1-2° increments from DocLayNet/SROIE/Arabic) | Script ready; ~20K images generated |
| 2 | Curate symmetric document orientation samples (blank pages, figure-only, symmetric grids) | ~500 symmetric orientation samples |
| 2 | Build resolution confound sub-dataset (DocLayNet PDFs at 72/150/300 DPI) | ~2K confound images |

### Track F — Long-Lead Item Resolution (Weeks 3-6)

**Goal**: Receive and process long-lead acquisitions from Track A; build ILLEGIBLE class.

| Week | Action | Deliverable |
|---|---|---|
| 3-4 | Process received handwriting datasets; run SHA256/pHash dedup against training manifests | Deduped handwriting data ready |
| 4-5 | ILLEGIBLE class curation: filter degraded pages from KHATT (OCR WER > 0.80) + CASIA (high-noise) + IAM (degraded writers) | ~650 ILLEGIBLE candidates from real data |
| 5-6 | ILLEGIBLE synthetic augmentation: apply heavy noise + blur + contrast collapse to MODERATE/POOR samples; accept if WER > 0.80 | ~500 synthetic ILLEGIBLE (total ≥1,000) |
| 5-6 | Human verification of ALL ILLEGIBLE labels (mandatory — no model-only labels) | ≥1,000 human-verified ILLEGIBLE samples |

---

## §5 — Phase 2: Coverage Assessment

**When**: After Phase 1 real data gathering is substantially complete (~Week 4-6).

**Purpose**: Determine exactly how much synthetic data each head still needs by measuring
the gap between real data placed and ideal corpus targets.

### Step 1: Run Diversity Audit

```bash
# Run full diversity evaluation across all 10 training datasets
uv run python scripts/evaluate_dataset_diversity.py --all-datasets

# Generate cross-tabulation report
uv run python scripts/verify_dataset_diversity.py --cross-tab
```

### Step 2: Calculate Per-Head Gap

For each of the 10 training datasets, measure real data placed vs. ideal target:

| Dataset | Ideal Size | Real Acquired (Phase 1) | Gap (synthetic fill target) | Synthetic Cap | Max Synthetic |
|---|---|---|---|---|---|
| Orientation | 50,000 | _[measured]_ | 50,000 - real | ≤40% | 20,000 |
| Skew | 90,000 | 90,412 ✅ | 0 | ≤37.5% | N/A |
| Post-Correction Skew | 20,000 | _[measured]_ | 20,000 - real | ≤40% | 8,000 |
| Resolution Quality | 30,000 | _[measured]_ | 30,000 - real | ≤17% | 5,100 |
| IQA (hard + pseudo) | ~125,000 | _[measured]_ | 125,000 - real | Phase 2 pseudo ≤50% | 62,500 |
| Script Detection | 108,000 | _[measured]_ | 108,000 - real | ≤60% | 64,800 |
| Handwriting | 60,000 | _[measured]_ | 60,000 - real | Negatives only | ~6,000 |
| Capture Method | 50,000 | _[measured]_ | 50,000 - real | Strict 0% production | 0 (production classes) |
| Shadow | ~18,000 | _[measured]_ | 18,000 - real | ≤50% | 9,000 |
| Warping | ~24,000 | _[measured]_ | 24,000 - real | ≤30% | 7,200 |
| Code Detection | 10,000 | _[measured]_ | 10,000 - real | ~50% (generation) | 5,000 |

### Step 3: Verify Acceptance Criteria

Check each of the 15 corpus acceptance criteria
([UTC §11](../datasets/UNIFIED_TRAINING_CORPUS.md#11--corpus-acceptance-criteria)) against
real data alone. Classify each criterion as:

- **PASS with real only**: No synthetic needed
- **PASS with synthetic fill**: Known synthetic capability closes the gap
- **BLOCKED**: Neither real nor synthetic can close the gap (requires Phase 4 remediation)

### Step 4: Prioritize Synthetic Fill

Rank synthetic fill by impact:

1. **Release 1 heads closest to threshold** (smallest gap → fastest to close)
2. **Release 1 scope** (16 heads: all except 5 HW heads + SIG-G3-2)
3. **Release 2 scope** (6 deferred heads: G4-1 to G4-5 + SIG-G3-2)

---

## §6 — Phase 3: Synthetic Fill

**When**: After Phase 2 coverage assessment identifies exact gaps (~Week 5-7).

**Purpose**: Generate synthetic data to fill remaining gaps using existing scripts and
pipelines. Verify no dataset exceeds its synthetic mixing cap.

### Known Synthetic Capabilities

| Capability | Script/Tool | Output | Status | Tier C Rank |
|---|---|---|---|---|
| v3 completion (190K → 350K) | `generate_base_dataset_v3.py` | Multi-script base images | Bug fixed; not run | C1 |
| Orientation real component | `build_orientation_real_component.py` | ~11K real orientation images | Script ready | C2 |
| Orientation synthetic views | `derive_v3_orientation_view.py` | ~20K non-Latin rotations | Script ready | C3 |
| Shadow overlay views | `generate_v3_shadow_view.py` | ~8K shadow images (4 types) | Script ready | C4 |
| Warping transform views | `generate_v3_warping_view.py` | ~5K warped images | Script ready | C5 |
| Code detection | `generate_code_detection_dataset.py` | ~10K code images | 8,613 dry-run | C6 |
| IQA compound distortion | _[to build in Track E]_ | 3-5K compound images | Pipeline needed | B1 |
| Narrow-range skew | _[to build in Track E]_ | ~20K ±2° images | Script needed | B2 |
| OOD synthetic generation | Various scripts in OOD plan | ~4,221 OOD images | Scripts ready | C7 |

### Fill Sequencing (Dependency Order)

Generation must proceed in this order due to dependencies:

1. **v3 completion run** (C1) — gates all v3-derived views; must complete before C3-C5
2. **Shadow view generation** (C4) — requires Tier 0 severity labels (Track B)
3. **Warping view generation** (C5) — requires Tier 0 severity labels (Track B)
4. **Orientation view generation** (C3) — independent; can run in parallel with C4/C5
5. **Orientation real component** (C2) — independent
6. **Code detection generation** (C6) — independent
7. **IQA compound distortion** (B1) — independent
8. **Narrow-range skew generation** (B2) — independent

### Synthetic Cap Verification

After fill, verify no dataset exceeds its synthetic mixing cap:

| Dataset | Synthetic Cap | Expected Real | Expected Synthetic | Expected % Synthetic | Pass? |
|---|---|---|---|---|---|
| Orientation | ≤40% | ~32K (DocLayNet + RVL-CDIP) | ~20K (v3 non-Latin) | ~38% | ✅ |
| Skew | ≤37.5% | ~50K natural | ~40K synthetic rotation | ~44% | ⚠️ Over cap |
| Shadow | ≤50% | ~11.7K (sd7k + wsrd + negatives) | ~8K (v3 overlay) | ~41% | ✅ |
| Warping | ≤30% | ~19.8K (5 real paired GT datasets) | ~5K (v3 transforms) | ~20% | ✅ |
| Script Detection | ≤60% | ~48K (MDIW13 real + rebalanced real subset) | ~60K (v3 stratified) | ~56% | ✅ |
| Code Detection | ~50% | ~5K (curated negatives) | ~5K (PIL+Pygments generated) | ~50% | ✅ |

**Skew cap violation note**: The existing skew dataset is 79.1% synthetic vs. the ≤37.5%
ideal cap. This is documented as an AT RISK item in the corpus review. Increasing the
natural scan component requires acquiring more real-scan datasets with reliable skew
labels — this should be addressed in Phase 4 if the training run confirms the synthetic
gap causes performance degradation.

---

## §7 — Phase 4: Final Gap Remediation

**When**: After Phase 3 synthetic fill is complete (~Week 7+).

**Purpose**: Address remaining gaps that neither real acquisition nor synthetic
generation fully closed.

### Expected Remaining Gaps

| Gap | Likely Cause | Remediation Options |
|---|---|---|
| VLM IQA fallback | SRCC gate may never reach 0.65 | Option A: train on 25K hard labels only (reduced accuracy). Option B: use ensemble of classical IQA detectors as pseudo-labeler. Option C: procure human MOS labels for 5K additional images. |
| Handwriting dataset expansion | One or more P0 acquisitions may be rejected or delayed | Option A: synthetic handwriting generation (style transfer). Option B: alternative public datasets (Muharaf, SCUT-HCCDoc). Option C: defer specific script families to Release 3. |
| Modern CIS flatbed | No known public dataset of 2010+ CIS scanner output | Option A: acquire MIDV-2020 or similar. Option B: internal scanning (physical Fujitsu ScanSnap or similar). Option C: accept limitation and document in model card. |
| Skew synthetic cap | 79.1% synthetic vs 37.5% target | Option A: acquire additional real-scan datasets. Option B: increase natural scan Hough+projection labeling quality to accept more borderline samples. |
| OOD corpus scaling | 9,155 of 12,000 target (76.3%) | Continue phased OOD build per OOD corpus plan; synthetic scripts can cover ~4,221 remaining. |
| Wild condition gaps | UTC §8 has 8 conditions, most at 0% coverage | Address per-condition: compound distortion (Phase 1B pipeline), book gutter (Track E), fax halftone (Track D), mobile defocus (MIDV500 subset), etc. |
| Cross-tabulation cells | 5×6 script×degradation matrix may have 0-cells | Generate targeted synthetic samples for empty cells using v3 + Augraphy per-script degradation. |

### OOD Evaluation Dataset Status

The OOD evaluation dataset (12-15K target, 9,155 acquired as of 2026-02-25) is
**adequate for directional validation** of all 22 heads. It does not impact the
training corpus directly but provides the diagnostic layer that identifies which heads
fail in production. See [OOD_DATASET_CATALOG.md](../datasets/OOD_DATASET_CATALOG.md)
for the full specification.

**AT-RISK OOD heads** requiring intervention:

- `resolution_quality`: 365 images need model inference labeling
- `skew_score`: Needs trained MobileNetV4 inference over all 9,155 images
- `handwriting_legibility`/`_score`: Needs human annotators for ~950 images

---

## §8 — Sequencing Integration with Master Plan

This section maps the four gathering phases to the
[MASTER_PROJECT_PLAN.md](MASTER_PROJECT_PLAN.md) tier structure.

### Phase-to-Tier Mapping

| Gathering Phase | Master Plan Tier | Key Actions | Duration |
|---|---|---|---|
| Phase 1 Track B (GPU labeling) | **Tier 0** | Shadow/warping severity labeling; resolution V2 | Weeks 1-3 |
| Phase 1 Track A (handwriting acquisition) | **Tier 1 / Tier 3** (Stream 4E) | Parallel to other Tier 1 work; long-lead | Weeks 1-6 |
| Phase 1 Track C (VLM gate) | **Tier 1** | Determines IQA pseudo-label path | Weeks 1-4 |
| Phase 1 Track D (heuristic labeling) | **Tier 1** | ADF + FAX class labeling | Weeks 2-4 |
| Phase 1 Track E (assembly) | **Tier 1** | IQA compound, narrow skew, book gutter | Weeks 2-4 |
| Phase 2 (coverage assessment) | **Tier 1 → Tier 2 gate** | Run before GCS upload | Weeks 4-6 |
| Phase 3 (synthetic fill) | **Tier 1** | Run view generation scripts | Weeks 5-7 |
| Phase 4 (gap remediation) | **Tier 2+** | Ongoing through training | Weeks 7+ |

### Critical Path

The critical path to training readiness runs through:

1. **Track B** (GPU labeling, Weeks 1-3) → unblocks shadow/warping assembly
2. **Phase 3** (synthetic fill, Weeks 5-7) → provides remaining synthetic data
3. **Phase 2** (coverage assessment, Weeks 4-6) → gates GCS upload (Tier 2)
4. **Tier 2** (GCS upload + DDRs #9/#10) → gates SigLIP 2 training (Tier 3)

Handwriting acquisition (Track A) runs in parallel but does NOT block Release 1 training.
The 5 handwriting heads (G4-1 to G4-5) are deferred to Release 2 per the
[TRAINING_DATA_STRATEGIC_ANALYSIS.md](TRAINING_DATA_STRATEGIC_ANALYSIS.md) conditional
Go decision.

### Release Alignment

| Release | Heads | Gathering Dependency |
|---|---|---|
| Release 1 (16 heads) | MNV4 (3) + G1 IQA (6) + G2 Script (1) + G3-1 (1) + G5 Page Attrs (5) | Phases 1-3 complete; Phase 4 ongoing |
| Release 2 (6 heads) | G3-2 (post-correction skew) + G4 Handwriting (5) | Track A acquisition complete; B2 narrow-range skew built; ILLEGIBLE class populated |

---

_This document is the authoritative sequencing guide for all dataset acquisition and
assembly work. For what the corpus must look like, see
[UNIFIED_TRAINING_CORPUS.md](../datasets/UNIFIED_TRAINING_CORPUS.md). For implementation
scripts and manifest generation, see
[MASTER_PROJECT_PLAN.md §6](MASTER_PROJECT_PLAN.md) Tier 1 (Stream 4B)._
