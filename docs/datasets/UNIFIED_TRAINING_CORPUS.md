# Unified Training Corpus — Ideal-State Specification

> **Status**: Active | Specification Document
> **Version**: 1.0.0
> **Created**: 2026-02-23
> **Updated**: 2026-02-23
> **Purpose**: Authoritative specification defining what the unified training corpus must look like
> to support reliable training of all 22 model heads. This is an ideal-state specification —
> it defines *what* the corpus must satisfy, not *how* to build it.

---

## Table of Contents

1. [Corpus Identity](#1--corpus-identity)
1b. [Unique Source Pool Analysis](#1b--unique-source-pool-analysis)
2. [Head Coverage Requirements](#2--head-coverage-requirements)
3. [Ideal Corpus Composition](#3--ideal-corpus-composition)
4. [14-Dimension Diversity Coverage Requirements](#4--14-dimension-diversity-coverage-requirements)
5. [Ideal Split Structure and Provenance Requirements](#5--ideal-split-structure-and-provenance-requirements)
6. [Label Quality Requirements](#6--label-quality-requirements)
7. [Synth-Multiscript v3 as Multi-Task Backbone](#7--synth-multiscript-v3-as-multi-task-backbone)
8. [Wild Condition Coverage Requirements](#8--wild-condition-coverage-requirements)
9. [What the Corpus Explicitly Excludes](#9--what-the-corpus-explicitly-excludes)
10. [Corpus Verification Framework](#10--corpus-verification-framework)
11. [Gap Registry](#gap-registry)
12. [Corpus Acceptance Criteria](#11--corpus-acceptance-criteria)
13. [Current State vs Ideal (Gap Summary)](#12--current-state-vs-ideal-gap-summary)

---

## §1 — Corpus Identity

The ideal corpus is **one global corpus**, not ten separate per-head datasets. It maintains a single shared backbone split registry keyed on SHA256 image hashes, and serves all 22 model heads simultaneously through per-head filtered views derived from that shared registry. This design is not incidental — it is a direct consequence of the SigLIP 2 NAFlex architecture.

SigLIP 2 has a shared backbone (86M params, 768-dim feature vector) from which all 19 task heads draw. Any image seen during training for any head means the backbone has been exposed to that image's visual content. If the same image appears as a training sample for one head but a test sample for another, the backbone weights reflect that image, and the test evaluation is contaminated. The global split registry eliminates this failure mode: an image's `split_type` applies to every head simultaneously.

MobileNetV4-Conv-S has three independent heads (orientation, skew, resolution quality) but is trained from the same dataset views as SigLIP's corresponding heads. The global split registry enforces leakage prevention across both models.

Key properties the ideal corpus must exhibit:

- A single corpus manifest conforming to `docs/schema/corpus_manifest_v1.schema.json`, with every record carrying a SHA256-keyed `corpus_id` as its primary key.
- Every sample must appear in exactly one split across all heads: `train`, `val`, `test`, `ood`, or `reserved`. No image may be `train` for one head and `test` for another.
- Val and test assignments must be immutable once locked. OOD assignments are one-way (no reversion to train).
- The reserved pool must contain a supersample of large source datasets (e.g., ~88% of RVL-CDIP 400K starts reserved) to enable OOD expansion without contaminating training splits.
- Every sample in every training manifest must carry a `provenance` field (`real_scan`, `real_camera`, `real_born_digital`, `real_paired`, or `synthetic_v3`). This field is enforced at manifest generation time by `scripts/prepare_multitask_datasets.py` and enables post-hoc real/synthetic gap analysis.
- No cross-dataset semantic duplicates may appear in val or test splits (pHash Hamming distance ≤ 5 screens near-duplicates at ingestion time).

The corpus serves 10 distinct training dataset views (orientation, skew, resolution quality, IQA, script detection, handwriting, capture method, shadow, warping, code detection). These views share source images where appropriate — the same DocLayNet page may contribute to orientation, skew, resolution quality, handwriting, and capture method views. The global split registry ensures these shared contributions land in the same split everywhere.

Source references: `docs/schema/corpus_manifest_v1.schema.json`, `docs/architecture/diagrams/level-2/data-preparation/index.md §UTC`.

---

## §1b — Unique Source Pool Analysis

> **Source**: 4-model consensus analysis (Gemini 2.5 Pro, Gemini 3 Pro Preview, DeepSeek R1
> 0528, Grok 4; 2026-02-26) examining the relationship between per-head ideal sizes and
> actual unique images required. This section documents the corrected total unique image
> requirement and the cross-dataset sharing that reduces it.

### Naive vs. Actual Unique Image Requirement

The 10 training datasets sum to approximately 565K images when counted per-head:

| Dataset | Ideal Size |
|---|---|
| Orientation | 50,000 |
| Skew | 90,000 |
| Post-Correction Skew (SIG-G3-2) | 20,000 |
| Resolution Quality | 30,000 |
| IQA (hard + pseudo) | ~125,000 |
| Script Detection | 108,000 |
| Handwriting | 60,000 |
| Capture Method | 50,000 |
| Shadow | ~18,000 |
| Warping | ~24,000 |
| Code Detection | 10,000 |
| **Naive per-head total** | **~565,000** |

However, the global corpus design (§1) means many source images serve multiple heads
simultaneously through different task-specific views. The actual unique image requirement
is **~420-440K**, a ~22% reduction from the naive sum. The per-head counts remain valid —
each head still needs the specified sample counts to learn its task adequately — but the
total unique images that must be acquired, stored, and managed is significantly lower.

### Cross-Dataset Sharing: Three Major Source Pools

Three source pools account for the majority of cross-head sharing. Each pool contains
unique images that are reused across multiple heads through derived views (§7).

**Pool 1 — Synth-Multiscript v3 (190,485 unique images → ~140K view-entries)**

| Head View | Images Used | Selection Criteria |
|---|---|---|
| Script Detection | ~60K | All 27 scripts, weighted resampling for class balance |
| Orientation (synthetic component) | ~20K | Non-Latin scripts only (19 scripts) |
| Skew (synthetic component) | ~10K | Stratified by script and DPI tier |
| Resolution Quality | ~5K | Stratified across all 7 DPI tiers |
| IQA Phase 2 pseudo-labels | up to 20K | Diverse subset across quality tiers |
| Shadow synthetic | ~8K | Augraphy shadow overlay (4 types) |
| Warping synthetic | ~5K | Perspective/page_curl/fold transforms |
| Capture Method | ~7.5K | Labeled as `capture_method=synthetic` |
| Handwriting negatives | ~5K | Printed-only subset (NONE class) |
| **Total view-entries** | **~140K** | from 190K unique base images |

Most v3 images serve 2-4 views. A single v3 image used for script detection, orientation
rotation, and shadow overlay counts as 1 unique image but 3 view-entries. The effective
multiplier is ~0.74x (140K views / 190K unique).

**Pool 2 — DocLayNet (~50K used of 81K available → ~80K view-entries)**

| Head View | Images Used | Usage |
|---|---|---|
| Orientation (real component) | ~32K | Born-digital PDFs rotated to 4 classes |
| Resolution Quality | ~5K | Multi-DPI renders (72/150/300 DPI) |
| IQA Phase 2 pseudo-labels | ~10K+ | VLM pseudo-labeled subset |
| Handwriting negatives | ~15K | Printed-only subset |
| Capture Method (BORN_DIGITAL) | ~15K | Native PDF category |
| Code Detection negatives | ~3K | Non-code printed documents |

DocLayNet is the highest-leverage real dataset: each acquired page serves 5-6 heads.
The effective multiplier is ~1.6x (80K views / 50K unique).

**Pool 3 — RVL-CDIP (~50K used of 400K available → ~35K view-entries)**

| Head View | Images Used | Usage |
|---|---|---|
| Orientation (real component) | ~12K | Scanned documents rotated to 4 classes |
| Capture Method (SCANNER_FLATBED, SCANNER_ADF, FAX) | ~12.5K | Multiple scanner categories |
| IQA Phase 2 pseudo-labels | ~10K+ | VLM pseudo-labeled subset |

The remaining ~350K RVL-CDIP images start as `corpus_status: reserved`, providing a clean
pool for future OOD expansion or training augmentation.

### Unique Source Pool Summary

| Source Pool | Unique Images | Head Views Served | Sharing Pattern |
|---|---|---|---|
| Synth-multiscript v3 | ~190K | 7-9 heads via derived views | High: same base image, different transforms |
| DocLayNet | ~50K (of 81K available) | 5-6 heads | High: same page, different labels extracted |
| RVL-CDIP | ~50K (of 400K; 88% reserved) | 3-4 heads | Moderate: orientation + capture + IQA |
| Specialized real datasets | ~100K combined | 1-2 heads each | Low: sd7k, wsrd, KHATT, CASIA-HWDB, IIIT-INDIC, HKR, IAM, HierText, anyphotodoc6300, warpdoc, docalign12k, MIDV500, SmartDoc-QA, etc. |
| Specialized synthetic | ~30K combined | 1-2 heads each | Low: code detection generation, narrow-range skew, IQA compound distortion |
| **Total unique images** | **~420-440K** | | |

### Implications for Corpus Assembly

1. **Acquisition efficiency**: Multi-head source pools (DocLayNet, v3, RVL-CDIP) deliver
   more value per acquired image than single-head sources. A single DocLayNet page serves
   5-6 heads; a single sd7k image serves only 1 (shadow).

2. **Real data as the bottleneck**: Specialized real datasets (handwriting scripts,
   shadow/warping paired GT, modern CIS flatbeds) have a ~1.0x sharing multiplier — they
   serve few heads but are irreplaceable for those heads. This makes them the primary
   bottleneck for corpus completion and justifies prioritizing their acquisition first.
   See [DATASET_GATHERING_STRATEGY.md](../planning/DATASET_GATHERING_STRATEGY.md) for
   the acquisition sequencing plan.

3. **Split registry scale**: The global split registry (SHA256-keyed) must accommodate
   ~420-440K unique entries, not 565K. This affects manifest generation performance,
   dedup verification scope, and storage planning.

4. **v3 completion economics**: Completing v3 from 190K to 350K would proportionally
   increase multi-head coverage, but the marginal benefit per image decreases as
   cross-head overlap is already high for existing images.

---

## §2 — Head Coverage Requirements

The table below specifies the minimum requirements for each of the 22 model heads. Performance targets define what acceptable generalization looks like. Minimum training samples are lower bounds, not targets — the actual ideal size for each dataset is specified in §3. Key distribution requirements capture the structural constraints that produce a robust model; violations typically manifest as systematic failures on underrepresented subgroups, not as globally poor metrics.

**MobileNetV4 Heads (3)**

| Head | Task | Output | Performance Target | Min Training Samples | Key Distribution Requirements |
|---|---|---|---|---|---|
| MNV4-H1 | orientation_cls | 4-class (0/90/180/270) | ≥95% accuracy on non-ambiguous inputs | 50,000 | ≥60% real documents; 4 classes balanced ±3%; ~2,500 samples labeled `orientation_ambiguous`; abstention rate ≥85% on ambiguous inputs; non-Latin scripts ≥5% of set |
| MNV4-H2 | skew_reg | Regression ±10° | MAE < 0.5° (val); SRCC > 0.93 | 90,000 | ≥62.5% natural scan; 7-bin angle distribution per §3; ≥20% multi-column layouts; Hough+projection agreement within 0.5° required for multi-column labels (conf≥0.7 filter) |
| MNV4-H3 | resolution_quality_reg | 0–1 continuous | MAE < 0.1 within-bucket | 30,000 | All 7 DPI tiers present (72/100/150/200/300/400/600); confound sub-dataset (~2K) mandatory; raw physical metrics (`pixel_height`, `stroke_width`, `contrast_ratio`) output alongside score |

**SigLIP 2 Group 1 — IQA (6 heads)**

| Head | Task | Output | Performance Target | Min Training Samples | Key Distribution Requirements |
|---|---|---|---|---|---|
| SIG-G1-1 | blur_score | Regression 0–1 | VQualA ≥ 0.92 | ~25K hard + 100K pseudo | Compound distortion sub-split (3–5K) mandatory as separate held-out eval; no single distortion type >60% |
| SIG-G1-2 | noise_score | Regression 0–1 | VQualA ≥ 0.92 | Same IQA dataset | Compound sub-split mandatory; camera ≥30% of Phase 1 hard labels |
| SIG-G1-3 | contrast_score | Regression 0–1 | VQualA ≥ 0.92 | Same IQA dataset | ≥5 distortion types at severity >0.3; script×degradation cross-tab ≥100 per cell |
| SIG-G1-4 | skew_score | Regression 0–1 | VQualA ≥ 0.92 | Same IQA dataset | Note: IQA skew severity (quality signal) is distinct from MNV4-H2 skew angle (correction angle) |
| SIG-G1-5 | compression_score | Regression 0–1 | VQualA ≥ 0.92 | Same IQA dataset | JPEG quality <50 samples required; JPEG blockiness explicitly covered |
| SIG-G1-6 | overall_quality | Regression 0–1 | VQualA ≥ 0.92; human MOS SRCC ≥ 0.65 after non-rotated correction | Same IQA dataset | Human annotation tier_1 required for primary training labels; VLM pilot SRCC ≥ 0.60 before scaling pseudo-labels |

**SigLIP 2 Group 2 — Script (1 head)**

| Head | Task | Output | Performance Target | Min Training Samples | Key Distribution Requirements |
|---|---|---|---|---|---|
| SIG-G2-1 | script_cls | 19 ML classes | ≥90% overall; Tibetan ≥80% | 108,000 balanced | Mong/Syrc/Geor permanently excluded from training; max class imbalance 3×; ≥5 font families per script; class weights TIBT=2.0, SE_ASIAN_OTHER=1.8, GREK=1.5 |

**SigLIP 2 Group 3 — Orientation + Skew (2 heads, post-correction)**

| Head | Task | Output | Performance Target | Min Training Samples | Key Distribution Requirements |
|---|---|---|---|---|---|
| SIG-G3-1 | orientation_cls (post-correction) | 4-class | ≥98% accuracy | Same as orientation dataset | Images are post-correction (already upright); provides validation of MNV4-H1 and teacher signal for future distillation |
| SIG-G3-2 | skew_reg (post-correction) | Regression ±10° | MAE < 0.3° | Same as skew dataset | Tighter target reflects coarse orientation already resolved; provides teacher signal for MNV4-H2. **⚠️ NOTE: The existing 90K skew dataset covers full ±45° range for MNV4-H2. SIG-G3-2 requires a SEPARATE ±2° narrow-range subset (~20K images) focusing on sub-degree precision. These are distinct deliverables.** |

**SigLIP 2 Group 4 — Handwriting (5 heads)**

| Head | Task | Output | Performance Target | Min Training Samples | Key Distribution Requirements |
|---|---|---|---|---|---|
| SIG-G4-1 | handwriting_presence_cls | 5-class (NONE/SPARSE/MODERATE/SUBSTANTIAL/DOMINANT) | ≥88% | 60,000 | NONE 35%, SPARSE 15%, MODERATE 20%, SUBSTANTIAL 15%, DOMINANT 15% (±5% tolerance); KHATT/CASIA-HWDB/IIIT-INDIC/HKR are P0 prerequisites |
| SIG-G4-2 | handwriting_legibility_cls | 6-class (NOT_APPLICABLE/EXCELLENT/GOOD/FAIR/POOR/ILLEGIBLE) | ≥85% | Same handwriting dataset | ILLEGIBLE ≥1,000 samples (≥5%); tier_1 annotation required for legibility labels; tier_3 weight capped 0.4 |
| SIG-G4-3 | handwriting_content_type_cls | 7-class (not_applicable/signatures/numeric/alphanumeric/prose/mixed/specialized) | Per-class accuracy targets | Same handwriting dataset | specialized ≥500 samples; all 7 classes present |
| SIG-G4-4 | presence_reg | 0–1 continuous | MAE < 0.15 | Same handwriting dataset | Mid-range presence (0.2–0.7 area ratio) ≥20%; tier_3 weight capped 0.4 |
| SIG-G4-5 | legibility_reg | 0–1 continuous | MAE < 0.15 | Same handwriting dataset | Full score range (0–1) covered; human calibration recommended for heuristic tiers |

**SigLIP 2 Group 5 — Page Attributes (5 heads)**

| Head | Task | Output | Performance Target | Min Training Samples | Key Distribution Requirements |
|---|---|---|---|---|---|
| SIG-G5-1 | capture_method_cls | 7-class | ≥85% | 50,000 | SCANNER_ADF ≥2,500; FAX ≥2,500 (heuristic-labeled); SCANNER_FLATBED modern CIS (2010+) ≥1,500 samples |
| SIG-G5-2 | shadow_reg | 0–1 | MAE < 0.08 | ~18,000 | ≥50% real paired GT; book gutter shadow required (Gap 5 — do not mark complete without it); SSIM labels permanently invalid |
| SIG-G5-3 | warping_reg | 0–1 | MAE < 0.08 | ~24,000 | ≥70% real paired GT; all warping types present; SSIM labels permanently invalid |
| SIG-G5-4 | code_cls | 0–1 | Precision >0.8 at >0.5 threshold | 10,000 | 8 programming languages; 4 rendering styles; handwritten code ≥500 samples. **⚠️ P0 ARCHITECTURAL FIX APPLIED: The training signal is boolean (has_code) — this head uses sigmoid + BCE loss, named `code_cls`.** |
| SIG-G5-5 | resolution_quality_reg | 0–1 | MAE < 0.1 (within 0.05 of MNV4-H3) | Same resolution dataset | Script-aware adjustments in inference only (CJK×0.55, Deva/Arab/Tibt×0.65); provides teacher signal and single-pass CPU fallback |

> **⚠️ Cross-Head Label Disambiguation — Mandatory Reading Before Label Assignment**
>
> **`skew_reg` vs `skew_score`**: These are different labels measured on different scales.
>
> - `skew_reg` (MNV4-H2, SIG-G3-2) = **geometric angle** of the physical document in degrees.
>   Range ±45° for MNV4-H2, ±2° for SIG-G3-2. Source: Hough transform or rotation metadata.
>   Do NOT use quality-proxy labels for this field.
> - `skew_score` (SIG-G1-4) = **quality degradation** caused by skew as perceived by OCR and
>   human readers. Score 0–1 (0 = no quality impact, 1 = maximum quality impact). NOT an angle.
>   Source: IQA labeling pipeline (VLM or OCR degradation estimate). Do NOT populate from Hough output.
>
> **`code_cls` (formerly `code_reg`)**: Binary classification (has_code 0/1), sigmoid + BCE loss,
> output range [0,1]. Decision threshold 0.5 for routing. Values 0.3–0.7 are "uncertain" — trigger
> conservative routing (assume no code). This head is renamed from `code_reg`; update all references.
>
> **N_A labels (all handwriting heads)**: Samples where a handwriting label is not applicable
> (e.g., purely printed documents in handwriting_legibility) MUST use `label_value = -1.0` with
> `masked_loss = true`. Do NOT use 0.0 — this creates a false training signal. Loss masking must be
> implemented in the training loop for all Group 4 heads.

---

## §3 — Ideal Corpus Composition

The table below summarizes the 10 training datasets at a glance. Detailed requirements for each follow.

| Dataset | Ideal Size | Synthetic Cap | Label Tier | Ideal Real:Synth | Priority |
|---|---|---|---|---|---|
| Orientation | 50,000 | ≤40% | tier_0_exact | ≥60%:≤40% | P0 (Stream 4C rebuild) |
| Skew | 90,000 | ≤37.5% | tier_0_exact + tier_2_model | ≥62.5%:≤37.5% | Complete |
| Resolution Quality | 30,000 | ≤17% | tier_0_exact + tier_3_heuristic | ≥83%:≤17% | P0 |
| IQA | ~25K hard + 100K pseudo | Phase 2 pseudo ≤50% weight | tier_1_annotation + tier_2_model | Phase 1: ~100% real | P0 |
| Script Detection | 108,000 balanced | ≤60% | tier_0_exact + tier_1_annotation | ≥40%:≤60% | P0 |
| Handwriting | 60,000 | Negatives only | tier_1_annotation + tier_3_heuristic | ≥90%:≤10% | P0 |
| Capture Method | 50,000 | Strict 0% production traffic | tier_1_annotation + tier_3_heuristic | 100% real | P1 |
| Shadow | ~18,000 | ≤50% | tier_0_exact + real_paired | ≥50%:≤50% | P1 |
| Warping | ~24,000 | ≤30% | tier_0_exact + real_paired | ≥70%:≤30% | P1 |
| Code Detection | 10,000 | ~50% (generation) | tier_0_exact + tier_1_annotation | ~50%:~50% | P1 |

---

### §3.1 Orientation Dataset (50K)

The ideal orientation dataset teaches the model to distinguish 90-degree increment rotations across the full diversity of document types encountered in production. Its defining property is that it is predominantly real: synthetic images can provide non-Latin script coverage (which real document corpora lack), but rotation orientation is a global geometric property best learned from real scans and born-digital renders.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| orientation_class | CRITICAL | 25% each (12,500 per class) | ≥22% per class |
| capture_method | IMPORTANT | camera ≥20%, scanner ≥30%, born_digital ≥20%, synthetic ≤40% | No single class >40% |
| script_family | IMPORTANT | Non-Latin ≥40% of synthetic component | Latin covered by real documents |
| domain | STANDARD | ≥5 domains at ≥5% each | ≥4 domains |
| layout_type | STANDARD | ≥3 layout types | simple_text ≤60% |
| resolution | STANDARD | ≥3 DPI tiers | Low/medium/high all present |
| degradation | STANDARD | Clean 50%, light-degraded 35%, moderate 15% | Both degraded buckets ≥10% |

**Source mix:** ~32K DocLayNet PDFs rotated (provenance: `real_born_digital`) + ~12K RVL-CDIP scans rotated (provenance: `real_scan`) + ~20K v3 non-Latin synthetic (provenance: `synthetic_v3`). Latin synthetic from v3 is excluded — Latin orientation is adequately covered by real documents, and synthetic Latin inflates the easy majority class without improving robustness.

**Ambiguous document handling:** ~2,500 samples (blank pages, figure-only pages, symmetric content, very sparse text) must be labeled `orientation_ambiguous`. Accuracy metrics are reported separately for standard vs. ambiguous inputs. The ambiguous class is not folded into the primary 4-class training loss; instead, a confidence-suppression target or separate binary head handles it. The abstention rate on ambiguous inputs must reach ≥85%.

**Known gap:** Non-Latin documents constitute approximately 1% of the current dataset (old configuration). The Stream 4C rebuild targets ≥40% non-Latin in the synthetic component, but the real component (DocLayNet + RVL-CDIP) remains predominantly Latin. This is an accepted structural limitation; synthetic v3 covers the non-Latin gap.

---

### §3.2 Skew Dataset (90K)

The ideal skew dataset teaches the model to estimate fractional-degree angular deviations with sub-0.5° precision across the full ±10° correction-relevant range. Its defining property is the deliberate over-representation of the mild skew range (±0.5–2°), which is where sub-0.5° accuracy matters most for deskewing quality.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| angle_distribution | CRITICAL | 7-bin uneven (mild ±0.5–2° largest bucket) | No single bin >40% |
| layout_type | IMPORTANT | Multi-column ≥20% | ≥15% multi-column |
| capture_method | IMPORTANT | Natural scan ≥62.5% | ≥55% natural scan |
| script_family | STANDARD | ≥3 families | Latin + 2 others |
| domain | STANDARD | ≥4 domains | ≥3 domains |
| resolution | STANDARD | ≥3 DPI tiers | All present |
| text_density | STANDARD | Sparse/moderate/dense all present | No single density >70% |
| combined_distortion | STANDARD | ≥5% with simultaneous warping | ≥3% |

**Angle distribution (7-bin target):** Extreme negative [-10°, -5°] 5,000; moderate negative (-5°, -2°] 8,000; mild negative (-2°, -0.5°] 7,000; near-zero (-0.5°, 0.5°] 5,000; mild positive (0.5°, 2°] 7,000; moderate positive (2°, 5°] 5,000; extreme positive (5°, 10°] 3,000. Total: 40,000 synthetic rotation. Natural scans: 50,000 (conf≥0.7 classical ensemble filter).

**Multi-column gate (mandatory):** For multi-column layout documents, Hough transform and projection-profile cross-detector agreement within 0.5° is required before accepting a natural scan label. Global projection profiles fail on multi-column layouts (column gutters create false optima). Reject multi-column samples with cross-detector disagreement >0.5° rather than accepting with uncertainty. Multi-column MAE must be reported separately from single-column MAE; acceptable ratio is ≤1.5×.

**Source:** 40,412 synthetic (exact angle rotation from DocLayNet, FUNSD, SROIE, Arabic, MDIW13, MLT19, JSSoDa, and others) + 50,000 natural scans from 13 real-scan datasets (conf≥0.7 classical ensemble labeling).

---

### §3.2b SIG-G3-2 Post-Correction Narrow-Range Skew Dataset (~20K)

This is a **separate deliverable** from the §3.2 main skew dataset. SIG-G3-2 operates on post-correction images where residual skew is at most ±2°. Training it on the full ±45° distribution produces a model optimized for the wrong task — wide-range correction, not sub-degree verification.

**Purpose:** Teach SIG-G3-2 to detect residual micro-skew after MobileNetV4 has already applied coarse deskew. Target: MAE < 0.3° on near-zero angles.

**Composition:**

| Source | Count | Notes |
|---|---|---|
| Natural scans from §3.2 main skew set | ~20,000 | Filtered to \|angle\| ≤ 2.0° from the Hough ensemble labels |
| Synthetic narrow-range (optional supplement) | 0 (excluded) | Sub-degree synthetic labels have measurement error > target MAE; excluded |

**Filtering:** Apply `|skew_angle_degrees| <= 2.0` and `label_confidence >= 0.8` to the §3.2 natural scan subset. The existing 90K skew dataset contains ~20K–25K samples in this range (mild buckets from the 7-bin distribution).

**Split registry:** SHA256 primary key shared with global registry. Separate `dataset_id = "skew_postcorrection_v1"` namespace to prevent split collisions with the full §3.2 set. Re-split 70/15/15 independently (no re-use of §3.2 val/test assignments for these samples).

**Label schema additions:**

- `post_correction = true` (boolean flag, distinguishes from pre-correction skew)
- `label_source = "hough_ensemble_verified"` (must pass cross-detector agreement)
- `label_confidence >= 0.8` (stricter than §3.2 main dataset's ≥0.7 gate)

**Why not use the §3.2 dataset directly for SIG-G3-2:** The backbone sees a very different distribution — near-vertical lines and subtle misalignment vs. dramatic angular offset. Mixing the two distributions degrades sub-degree precision without improving wide-range coverage. SIG-G3-2 is a precision head, not a general correction head.

**Status:** Not assembled. Derivable from existing §3.2 natural scan set via angle filter. No new data acquisition required.

---

### §3.3 Resolution Quality Dataset (30K)

The ideal resolution quality dataset teaches the model to distinguish between images that will and will not produce acceptable OCR output based on character-level resolution, regardless of stated DPI. Its defining properties are: uniform distribution across all 7 DPI tiers (72–600 DPI), mandatory confound sub-dataset, and mandatory raw physical metric output alongside the composite quality score.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| quality_score | CRITICAL | Uniform distribution across 7 bins | ≥8% per bin |
| DPI_level | CRITICAL | All 7 tiers (72/100/150/200/300/400/600) | ≥500 per tier |
| capture_method | IMPORTANT | Scanner ≥50%, born_digital ≥30% | Both present |
| script_family | IMPORTANT | ≥3 families including CJK | CJK mandatory (char height threshold differs) |
| text_density | STANDARD | Very_dense ≥15% | ≥10% very_dense |
| content_flags | STANDARD | Formula ≥15%, table ≥10% | Both present |

**Character height → quality score mapping (7-range piecewise):**

- <16px: 0.00–0.15 (needs major upscaling)
- 16–24px: 0.15–0.35 (needs light upscaling)
- 24–32px: 0.35–0.55 (acceptable for Latin; insufficient for CJK at <30px)
- 32–48px: 0.55–0.75 (optimal OCR range)
- 48–64px: 0.75–0.85 (good, slightly oversized)
- 64–96px: 0.85–0.95 (oversized)
- >96px: 0.95–1.00 (definitely oversized)

Script-aware adjustments apply at inference only (not model retraining): CJK char_height <30px → quality_score ×0.55; Devanagari/Arabic/Tibetan char_height <24px → quality_score ×0.65.

**Confound sub-dataset (mandatory, ~2K):** Pre-upscaled rasters (~1,000: bicubic-upscaled 72/100 DPI images where measured char_height reads artificially high but sharpness is low) + vector PDF at low effective DPI (~500: same PDF rendered at 72 DPI and 300 DPI, labeled by `effective_render_dpi`) + mixed confound (~500). This sub-dataset teaches the model to distinguish "large char_height from true high-resolution" from "large char_height from upscaling artifacts."

**Raw physical metrics mandatory:** The resolution head must output `pixel_height`, `stroke_width`, and `contrast_ratio` alongside `quality_score`. These raw values enable script-aware and confound-aware threshold updates in the inference logic layer without model retraining.

**Source:** ~20K multi-DPI renders (DocLayNet 5K + FUNSD/SROIE/NIST 2K + MDIW13 3K) + ~5K real camera captures (SmartDoc-QA + RealDAE + MIDV500) + ~5K synthetic variable-resolution (v3 sample) + ~2K confound sub-dataset.

---

### §3.4 IQA Dataset (~25K hard + 100K pseudo)

The ideal IQA dataset teaches 6 regression heads (blur, noise, contrast, skew severity, compression, overall quality) to score document image quality with human-aligned perceptual accuracy. Its defining properties are: a compound distortion sub-split as a mandatory separate held-out evaluation set, and a phase structure that distinguishes hard-labeled real documents (Phase 1) from pseudo-labeled documents (Phase 2).

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| degradation_type | CRITICAL | ≥5 distortion types; compound ≥10% of Phase 1B sub-split | No single type >60% |
| capture_method | IMPORTANT | Camera ≥30% (was 583, now ~8,475 samples — resolved via SmartDoc-QA + MIDV500) | ≥20% camera |
| document_age | IMPORTANT | Aged ≥10% | ≥5% aged |
| script_family × degradation | IMPORTANT | ≥100 per cell (5 scripts × 6 degradation types) | 0 cells at 0 |
| domain | STANDARD | ≥5 domains at ≥5% each | ≥4 domains |

**Phase 1A (Assembled — ~15,499 hard-labeled images):**

- DIQA-5000: 5,499 images (RQ labels via sauvola_cc_v2; IQA via classical pipeline)
- OHR-Bench: ~8,500 images (VLM-labeled blur/noise/contrast)
- RealDAE: ~1,200 images (real degradation, camera source)
- SmartDoc-QA: ~300 images (camera smartphone, known orientation)

**Phase 1B — Compound Distortion Sub-Split (mandatory, ~4,000 images):**
This sub-split is HELD OUT from Phase 1 training and used only for compound-distortion evaluation. It must be assembled before any Phase 1 training checkpoint is used for production evaluation.

- blur + JPEG (Gaussian σ=3 + JPEG q=40): 800 images
- blur + noise (Gaussian + Poisson): 800 images
- noise + contrast + JPEG (triple compound): 800 images
- shadow + blur (Augraphy shadow + motion blur): 800 images
- blur + skew + noise (geometric + quality compound): 800 images
- Source: Apply distortion stacks to Phase 1A images. Re-label all 6 IQA scores via VLM after distortion.

**Phase 1C — Supplementary Hard-Labeled (target ~8,000 additional images):**

- MIDV500: ~2,000 images (camera, ID documents — diverse capture conditions)
- OCR-Quality: ~2,000 images (scanned documents with OCR ground truth as quality proxy)
- Tobacco800: ~2,000 images (scanned, varied quality — dedup against training split required)
- SmartDoc-QA remaining: ~2,000 images (not already in Phase 1A)
- Combined Phase 1A + 1C target: ~25K hard-labeled images

**Phase 2 — VLM Pseudo-Labels (gate-controlled, target 100K):**
Proceed only after Gate 2 passes. Sources: DocLayNet + RVL-CDIP + Tobacco800 + SmartDoc-QA (not in training). Weight = 0.5 × VLM confidence.

**Note on IQA skew:** The IQA `skew_score` head (SIG-G1-4) measures skew as a quality degradation signal (severity 0–1). This is distinct from MNV4-H2 and SIG-G3-2, which predict the actual correction angle. Both coexist and serve different pipeline functions.

**VLM SRCC Decision Gate (mandatory — do not proceed to Phase 2 without passing):**

```text
Gate 1 — VLM Prompt v2.0 Validation (30–50 images):
  SRCC ≥ 0.60 → Proceed to Gate 2
  SRCC < 0.60 → Revise prompt; retry once. After 2 consecutive failures → FALLBACK PATH

Gate 2 — VLM Scale Validation (2,000–5,000 images):
  SRCC ≥ 0.65 → Proceed to Phase 2 pseudo-label generation (100K target, 0.5× loss weight)
  SRCC 0.60–0.65 → Use Phase 2 but cap at 50,000 images (reduced confidence)
  SRCC < 0.60 → FALLBACK PATH

FALLBACK PATH (if VLM overall_quality gate is never met after 2+ prompt iterations):
  1. Drop overall_quality (SIG-G1-6) from Phase 1 training entirely
  2. Substitute: derive overall_quality as weighted mean of 5 per-dimension scores:
     overall_quality = blur×0.30 + noise×0.20 + contrast×0.20 + compression×0.15 + skew_score×0.15
  3. Document in corpus manifest as label_source="derived_ensemble", label_tier="tier_3_heuristic"
  4. Hold SIG-G1-6 head training for Phase 2 re-run when VLM data becomes available
  5. Impact: SIG-G1-6 performance is directional only; downstream routing rules using
     overall_quality must be validated against the derived signal before production use
  6. Gate: Resume VLM scaling attempt when prompt SRCC > 0.60 on fresh 30-image batch
```

**Current gate status (2026-02-23):** SRCC = 0.53 (non-rotated) — GATE NOT MET. VLM scaling halted.

---

### §3.5 Script Detection Dataset (108K balanced)

The ideal script detection dataset teaches a 19-class classifier to identify writing systems at the page level with sufficient generalization across font variation, degradation, and text scope. Its defining property is that the reserved scripts (Mongolian, Syriac, Georgian) must never appear in any training manifest, regardless of future OpenLID expansion phases.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| script_class | CRITICAL | 19 classes each ~12,963 samples; max imbalance 3× | ≥5,000 per class |
| font_families | IMPORTANT | ≥5 font families per script | ≥3 font families |
| text_scope | IMPORTANT | 20% char, 25% word, 20% line, 35% page/doc | No single scope >40% |
| degradation | STANDARD | Degraded samples present per class | Clean ≤70% per class |

**Permanently reserved (never in training):** Mongolian (Mong) — TTB orientation anchor; Syriac (Syrc) — RTL anchor; Georgian (Geor) — LTR anchor with unique letterforms. The `_validate_no_reserved_scripts()` guard in `scripts/prepare_multitask_datasets.py` enforces this at manifest generation time.

**Per-class targets (19 classes):** LATN 30K (downsample from >100K available), ARAB 10K, DEVA 7K, HANS 6K, JPAN 6K, CYRL 5K, KORE 4K, TIBT 4K (P1 — only ~200 real page-level samples), BENG 3K, HEBR 3K, THAI 3K, TAML 2K, TELU 2K, GREK 2K, INDIC_OTHER 3K, SE_ASIAN_OTHER 2K, OTHER 3K, UNKNOWN 2K.

**Rebalancing requirement:** v3 has a confirmed distribution imbalance (Arab 49,169 = 3.8× target; 17 scripts below 12,963 target). Weighted resampling is required before training. This is not a regeneration task — the base images are correct; only the sampling ratios need adjustment.

**Source:** ~60K from v3 (stratified, rebalanced) + ~30K from MDIW13 train (13 scripts, real diversity) + ~5K COCO-Text + ~3K Arabic Docs OCR + ~3K SIW13 + ~2K CVSI + ~2K TibHCR (character composites for page-level Tibetan) + ~3K supplementary.

**Script Rebalancing Protocol (mandatory before any training manifest generation):**

| Step | Action |
|---|---|
| 1. Arab hard cap | Arab images contribute at most 13,000 to any training manifest. Flag is enforced via `--cap-arab 13000` in `prepare_multitask_datasets.py script` sub-command. |
| 2. Excess Arab disposition | The remaining ~36K Arab images (49K total − 13K cap) are marked `split_type="reserved"`. They are available for future expansion or OOD evaluation; never in training. |
| 3. Under-represented upsampling | 17 scripts below 12,963 target receive sampling weight `w = min(12963 / count, 3.0)`. Maximum weight cap of 3.0 prevents extreme oversampling. |
| 4. Backbone effect | Arab imbalance affects backbone weights (not just the script head). Rebalancing is mandatory before ANY head training — not only script-head training runs. |

**Per-class training weights (formal spec):**

| Class | Weight |
|---|---|
| TIBT (Tibetan) | 2.0 |
| THAI (Thai) | 1.8 |
| MYMR (Myanmar/Burmese) | 1.8 |
| LAOO (Lao) | 1.8 |
| KHMR (Khmer) | 1.8 |
| SINH (Sinhala) | 1.8 |
| GREK (Greek) | 1.5 |
| All other classes | 1.0 |

**Method**: Weighted sampling (not deletion, not regeneration). Each epoch samples from the full available pool with the weights above; no images are permanently removed from the dataset.

---

### §3.6 Handwriting Assessment Dataset (60K)

The ideal handwriting dataset teaches 5 heads (3 classification, 2 regression) to assess handwriting presence, legibility, and content type across scripts. Its defining property is that it is entirely real — synthetic font-based "handwriting" is used only for negatives (NONE class), never for positive handwriting examples.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| presence_class | CRITICAL | NONE 35%, SPARSE 15%, MODERATE 20%, SUBSTANTIAL 15%, DOMINANT 15% | ±5% from target per class |
| legibility_class | CRITICAL | ILLEGIBLE ≥5% (≥1,000 samples) | ILLEGIBLE ≥500 |
| handwriting_script | IMPORTANT | Latin/Arabic/CJK/Indic/Cyrillic all present | All 5 script families |
| content_type | IMPORTANT | All 7 content types present | specialized ≥500 |
| annotation_tier | IMPORTANT | Legibility: tier_1 required; tier_3 weight cap 0.4–0.5 | Tier_1 mandatory for legibility head |
| negative_class | STANDARD | ~22K printed-only (DocLayNet 15K + PubTabNet 5K + FinTabNet 2K) | ≥35% NONE class |

**P0 prerequisites (KHATT, CASIA-HWDB, IIIT-INDIC, HKR):** Without these four datasets, the handwriting heads cannot reliably classify Arabic cursive, CJK handwriting, Devanagari handwriting, or Cyrillic handwriting. These are not supplementary — they are prerequisites. Training must not begin without them.

**Source:** HierText (8.3K, gold standard: word-level handwritten+legible) + COCO-Text (~15K) + IAM (~5K, split by writer ID) + Muharaf (~5K, Arabic cursive) + PUCIT-OHUL (~3K) + KHATT (~4K, Arabic cursive) + CASIA-HWDB (~4K, CJK) + IIIT-INDIC (~3K, Devanagari+Indic) + HKR (~2K, Cyrillic) + Nepali Handwritten (958) + NIST SD-19 (~2K) + FUNSD (199) + printed-only negatives (~22K).

**ILLEGIBLE Class Acquisition Plan (≥1,000 samples required — currently void):**

The ILLEGIBLE class has 0 training samples as of 2026-02-23. Training must not begin until this class has at minimum 1,000 samples with human-verified labels. Target is 1,200 to provide a 20% buffer.

| Source | Target Count | Method | Notes |
|---|---|---|---|
| KHATT degraded pages | ≥200 | Human legibility rating < 2/5 | Already partially in OOD-Handwriting; dedup pass required |
| CASIA-HWDB high-noise pages | ≥200 | OCR WER > 0.80 on reference system | Automated WER filter + 10% human spot-check |
| IAM heavily-degraded writers | ≥150 | Classifier confidence < 0.4 on best available recognizer | From writerIDs already in training |
| Synthetic degradation of POOR samples | ≥500 | Augraphy heavy noise + extreme blur + contrast collapse on MODERATE/POOR samples; accept as ILLEGIBLE if post-distortion WER > 0.80 | Labeling: automated WER + human check |
| **Total** | **≥1,200** | | |

**Labeling protocol**: All ILLEGIBLE labels require human verification (not model-only). Labeler must confirm document content is genuinely unreadable, not merely low contrast.

**N_A Label Specification (CF-5 — mandatory for all Group 4 heads):**

For all 5 handwriting heads (SIG-G4-1 through SIG-G4-5), when a label is not applicable to a given sample (e.g., a purely printed document where handwriting_legibility is undefined):

- Set `label_value = -1.0` (NOT 0.0)
- Set `masked_loss = true` in the sample record
- The training loop MUST implement loss masking: samples with `masked_loss = true` are excluded from the loss computation for that head
- **Rationale**: Using 0.0 for N_A creates a false training signal (model learns "printed = ILLEGIBLE" or "printed = no presence"). The -1.0 sentinel with masked loss correctly excludes these samples.
- **Scope**: This applies to handwriting_legibility_cls (N_A when presence = NONE), handwriting_content_type_cls (N_A when presence = NONE), and legibility_reg/presence_reg when presence = NONE.

---

### §3.7 Capture Method Dataset (50K)

The ideal capture method dataset teaches a 7-class classifier to distinguish how a document was digitized. Its defining property is that it must contain zero synthetic images for the production-representative classes — synthetic documents are not representative of the capture artifacts that distinguish flatbed scanners from ADF scanners from smartphone cameras.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| capture_class | CRITICAL | 7-class with specific targets (see below) | SCANNER_ADF ≥2,500; FAX ≥2,500 |
| modern_CIS_flatbed | IMPORTANT | ≥1,500 samples from 2010+ CIS scanners | ≥1,000 |
| domain_spread | STANDARD | ≥5 domains | ≥4 domains |
| synthetic_cap | CRITICAL | 0% synthetic for production classes | Strict zero |

**7-class targets:** BORN_DIGITAL ~15K (born_digital PDFs rendered to image), SCANNER_FLATBED ~12.5K (RVL-CDIP, Tobacco800, NIST SD-2/SD-6, MDIW13 — must include ≥1,500 modern CIS 2010+ samples), SCANNER_ADF ~2.5K (RVL-CDIP ADF artifacts subset, heuristic-labeled — manual verification of 100 samples required before propagation), CAMERA_PROFESSIONAL ~5K (MIDV500, SmartDoc-QA), CAMERA_SMARTPHONE ~5K (SROIE, RealDAE, MLT19 camera subset), FAX ~2.5K (RVL-CDIP fax subset, heuristic-labeled), OTHER ~2.5K (screen recapture/moiré, SYNTHETIC sub-class).

**ADF heuristic (Gap 9):** Edge-parallel dark bands (2–5px near page margins), systematic micro-skew (consistent 0.2–0.8° per batch direction), paper-feed direction artifacts (horizontal streaks from roller dust), multi-page separator marks. Manual verification of 100 labeled samples required before propagation to full RVL-CDIP corpus.

**Modern CIS gap (Gap 8):** RVL-CDIP, Tobacco800, and NIST SD-2/SD-6 are 1990s CCD technology. Modern CIS flatbeds (2010+) produce different noise profiles, color rendition, and artifact patterns. A model trained only on 1990s scans will systematically misclassify modern flatbed captures. MIDV-2020 or equivalent recent flatbed scan dataset is required to supply ≥1,500 modern CIS samples.

**8th Class Addition — CAMERA_SMARTPHONE_APP (P1):**

Mobile document scanning apps (CamScanner, Adobe Scan, Microsoft Lens) produce distinctive artifacts that differ from raw smartphone camera captures:

- Perona-Malik edge sharpening (produces over-sharpened text edges)
- Auto-white balance overcorrection (paper appears unnaturally white)
- Software dewarping residuals (subtle curvature overcorrection at corners)
- JPEG with embedded app-specific EXIF metadata

| Attribute | Value |
|---|---|
| Class name | `CAMERA_SMARTPHONE_APP` |
| Target count | ≥1,500 images |
| Synthetic? | Strict zero (same rule as all other production classes) |
| Acquisition | Manual collection from CamScanner/Adobe Scan + Augraphy pipeline simulation |
| Priority | P1 (add in capture method dataset expansion, not initial assembly) |

Note: This makes capture_method_cls an 8-class head in total. Update `config/script_ml_classes.yaml` and training config when this class is added.

---

### §3.8 Shadow Dataset (~18K)

> **⚠️ Prerequisite: L2 Severity Labeling (Blocking)**
>
> `shadow_severity` and `shadow_type` fields are **not yet present** in L2 metadata for sd7k or wsrd.
> The Tier B real component (sd7k 7,239 images + wsrd 4,500 images) cannot be assembled until
> these labels exist. Run before dataset assembly:
>
> ```bash
> # Requires GPU VM (Vultr A100 or equivalent). Estimated compute: 4–6 hours.
> uv run python scripts/label_shadow_severity.py --input-dir /mnt/e/image_detection/01_base_data/sd7k/
> uv run python scripts/label_shadow_severity.py --input-dir /mnt/e/image_detection/01_base_data/wsrd/
> # Integrate results into L2 metadata:
> uv run python scripts/integrate_sd7k_enrichments.py --include-severity
> uv run python scripts/integrate_wsrd_enrichments.py --include-severity
> ```
>
> Outputs: `shadow_severity` (0–1) and `shadow_type` (edge/cast/spotlight/scanner_lid/book_gutter)
> per image. Acceptance criterion: L2 metadata fields populated for ≥95% of sd7k + wsrd images.

The ideal shadow dataset teaches a regression head to score shadow severity (0–1) across the diversity of shadow types encountered in camera-captured documents. Its defining properties are: ≥50% real paired ground truth, complete shadow type coverage, and permanent exclusion of SSIM-based severity labels.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| real_paired_GT | CRITICAL | ≥50% real (sd7k + wsrd + camera negatives) | ≥9,000 real samples |
| shadow_type | IMPORTANT | Edge/cast/spotlight/scanner_lid all present; book_gutter (Gap 5) | All 4 types; book_gutter P1 |
| severity_distribution | IMPORTANT | Uniform across 0–1 range | No severity gap >0.2 |
| stacked_degradation | STANDARD | ≥500 shadow+warping compound samples; weight 0.8× | ≤5% of dataset |
| color_mode | STANDARD | Binarized ≥10% (shadow_unmeasurable=True flagged) | Binarized documents flagged |

**Source composition:**

- Tier A synthetic (~8K): v3 base images with Augraphy shadow overlay (4 types: edge, cast, spotlight, scanner_lid). Severity = Augraphy severity parameter (tier_0_exact, confidence 1.0). Cap ≤50% of total.
- Tier B real (~7–10K): sd7k (7,239 flat-document paired GT, audit grade B 87) + wsrd (4,500 paired GT, audit grade A 95). Labels read from `shadow_severity` in L2 JSON; samples with `shadow_confidence < 0.5` skipped.
- Camera negatives (~3.5K): SmartDoc-QA clean frames (2,000) + MIDV500 flat captures (1,000) + v3 clean with zero shadow (500). These must come from the camera domain to avoid domain confound with positives.

**SSIM labels permanently invalid:** `severity = 1 − SSIM(shadow_img, clean_img)` is invalid for shadow because SSIM penalizes blur, noise, and compression equally — it cannot isolate shadow severity. This labeling approach is permanently abandoned (5-model consensus, 2026-02-21).

**Book gutter gap (Gap 5):** sd7k is flat-document only and does not capture book gutter or curved-page shadow patterns. Book spine shadows (gradient curves from physical binding) are a distinct artifact class. Do not mark shadow training complete without ≥1,000 book-gutter shadow samples.

---

### §3.9 Warping Dataset (~24K)

> **⚠️ Prerequisite: L2 Severity Labeling (Blocking)**
>
> `warping_severity` and `warping_type` fields are **not yet present** in L2 metadata for warpdoc,
> anyphotodoc6300, or wsrd. The Tier B real component cannot be assembled until these labels exist.
> Run before dataset assembly:
>
> ```bash
> # Requires GPU VM. Estimated compute: 2–3 hours.
> uv run python scripts/label_warping_severity.py --input-dir /mnt/e/image_detection/01_base_data/warpdoc/
> uv run python scripts/label_warping_severity.py --input-dir /mnt/e/image_detection/01_base_data/anyphotodoc6300/
> uv run python scripts/label_warping_severity.py --input-dir /mnt/e/image_detection/01_base_data/wsrd/
> # Integrate results:
> uv run python scripts/integrate_warpdoc_enrichments.py --include-severity
> uv run python scripts/integrate_anyphotodoc6300_enrichments.py --include-severity
> uv run python scripts/integrate_wsrd_enrichments.py --include-severity
> ```
>
> Outputs: `warping_severity` (0–1) and `warping_type` (perspective/page_curl/fold) per image.

The ideal warping dataset teaches a regression head to score page warping severity (0–1) across the diversity of distortion types encountered in camera-captured documents. Its defining properties are: ≥70% real paired ground truth (the highest real-data requirement of any dataset), complete warping type coverage, and permanent exclusion of SSIM-based severity labels.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| real_paired_GT | CRITICAL | ≥70% real (~17K) | anyphotodoc6300 + warpdoc + docalign12k at 0.3× |
| warping_type | IMPORTANT | Page_curl/fold/perspective/complex all present | All 4 types |
| severity_distribution | IMPORTANT | Uniform across 0–1 | No gap >0.2 |
| stacked_degradation | STANDARD | ≥500 warping+skew compound; weight 0.8× | Physical capture sequence: skew applied BEFORE warping |
| source_diversity | STANDARD | docalign12k at 0.3× weight (language gap); docreal 200; drccbi 325 | All four real sources present |

**Source composition:**

- Tier A synthetic (~5K): v3 base images with perspective/page_curl/fold transforms. Severity = normalized warp parameter (tier_0_exact, confidence 1.0). Cap ≤30% of total.
- Tier B real (~14–19.5K): anyphotodoc6300 (6,306 paired GT, grade A 92, AGPL-3.0) + warpdoc (1,020 paired GT, 6 distortion types, grade B 85) + docalign12k (all 12,000 pairs at 0.3× training weight due to grade D language gap) + docreal (200, MIT) + drccbi (325 paired GT).
- Warping negatives (~5K): SmartDoc-QA flat frames (3,000, severity=0.0) + MIDV500 flat captures (2,000, severity=0.0).

**SSIM labels permanently invalid:** Same rationale as shadow — SSIM measures structural similarity, not warping severity. This labeling approach is permanently abandoned (5-model consensus, 2026-02-21).

**docalign12k weight note:** Grade D (76) due to language gap (iso639=0%). Apply 0.3× training weight until domain enrichment completes. Despite down-weighting, all 12,000 pairs should be included — warping geometry labels remain valid even without domain metadata.

---

### §3.10 Code Detection Dataset (10K)

> **⚠️ Architectural Fix Applied: `code_reg` renamed to `code_cls`**
>
> This head was previously named `code_reg` but produces a binary output (has_code: true/false).
> The correct formulation is binary classification with sigmoid activation and BCE loss:
>
> - Loss function: `sigmoid + BCE`
> - Output range: [0, 1] (interpretable as has_code probability)
> - Decision threshold: 0.5 (values 0.3–0.7 are "uncertain" → conservative routing: assume no code)
> - Rename applied in: `SIGLIP2_MULTITASK_REQUIREMENTS.md`, `UNIFIED_TRAINING_CORPUS.md`
> - Also rename in: `modal/train_siglip2_multitask.py`, head registry, any inference scripts

The ideal code detection dataset teaches a binary classification head (`code_cls`) to score the probability that a document page contains programming code (0–1 confidence). Its defining property is balanced positive/negative construction: 5K code-positive and 5K code-negative samples, with explicit boundary cases in the 0.3–0.7 confidence range.

**Diversity requirements:**

| Dimension | Priority | Target | Minimum |
|---|---|---|---|
| positive_negative_ratio | CRITICAL | 50/50 | 45/55 to 55/45 |
| language_spread | IMPORTANT | 8 programming languages | ≥6 languages |
| rendering_style | IMPORTANT | Syntax-highlighted 40%, monospace 30%, inline 20%, handwritten 10% | All 4 styles present |
| boundary_cases | STANDARD | 0.3–0.7 confidence boundary cases explicit | ≥500 boundary cases |

**Source composition:**

- 5K positive: Python (25%), JavaScript (15%), Java (10%), C/C++ (10%), SQL (5%), other languages (15%), mixed code (20%). Rendering: Playwright or carbon-now-cli for GitHub-style renders (syntax-highlighted, realistic fonts and themes), monospace terminal renders, inline code snippets from technical documents, handwritten code (~500 samples).
- 5K negative: DocLayNet (3K, printed documents without code) + FinTabNet (2K, financial tables). Negatives must include mathematical notation that resembles code syntax (≥500 samples as boundary cases).

---

## §4 — 14-Dimension Diversity Coverage Requirements

An ideal corpus achieves the following distribution targets across all 14 diversity dimensions defined in the Layer 2 Enrichment Schema v6 (`docs/schema/layer2_enrichment_v2.schema.json`). These are corpus-level requirements: individual datasets may be narrower, but the combined corpus must satisfy each threshold.

| Dimension | Ideal Coverage | Per-Dataset Minimum | Why Critical |
|---|---|---|---|
| 1. capture_method | All 7 classes in ≥3 training datasets | No mono-capture dataset; camera ≥20% for IQA | Backbone must generalize across capture artifacts (scanner noise, camera perspective, PDF rasterization) |
| 2. domain | ≥5 domains per dataset | TAX/FIN/SCI/ADM/MED all present in corpus | Prevents domain overfit; OCR routing recommendations must generalize across industries |
| 3. script_code | ≥10 ISO 15924 codes in applicable datasets | 19 ML classes in script dataset; ≥5 font families per script | OCR routing depends on script detection; wrong script → wrong OCR engine |
| 4. script_family | Latin/CJK/Arabic/Indic/Cyrillic all represented | Arabic ≥5% orientation; CJK ≥15% handwriting | RTL/TTB correction behavior differs from LTR; char height thresholds differ by script |
| 5. resolution | ≥3 DPI tiers per dataset | 7 DPI tiers in resolution dataset (72–600) | Resolution head must generalize across DPIs; low-DPI failure mode is production-common |
| 6. text_density | Sparse/moderate/dense all present | No single density >70%; very_dense ≥15% in resolution | IQA metrics vary systematically with text density; IQA models trained on dense text fail on sparse |
| 7. layout_type | ≥3 layout types per dataset | Multi-column ≥20% in skew dataset (CRITICAL) | Multi-column breaks global skew estimation; systematic quality degradation on multi-column inputs if not represented |
| 8. content_flags | Table/formula/handwriting/figure each present | ≥15% formula, ≥10% table in resolution | SigLIP backbone context affects all head predictions; formula-dense pages have different char-height distributions |
| 9. degradation | ≥5 distortion types in IQA Phase 1B | No single distortion >60%; compound ≥10% of Phase 1B | VQualA requires generalized detection; single-degradation training produces 15–25% metric drop on real-world compound inputs |
| 10. content_type | Printed/handwritten/mixed all represented | Handwritten ≥30% script; NONE ≥35% handwriting | Presence classification boundary; backbone representation differs for handwritten vs. printed text |
| 11. handwriting | ILLEGIBLE/POOR present in legibility datasets | ILLEGIBLE ≥1,000 samples (5%) | Legibility head failure mode; ILLEGIBLE is rare but high-impact for routing decisions |
| 12. paper_size | A4/Letter/Legal/custom | No single size >60% | Prevent systematic size confound in layout and orientation heads |
| 13. color_mode | Binarized/grayscale/color all represented | Binarized ≥10% shadow; grayscale ≥25% script | shadow_unmeasurable flag required for binarized; script detection must survive grayscale (many historical documents) |
| 14. document_age | Modern/aged/historical | Aged ≥10% IQA; aged ≥15% + historical ≥5% in v3 | IQA heads must handle historical degradation patterns (foxing, ink fading, yellowing) |

**Cross-dimension interaction requirement:** A Chi-square test on (capture_method × script_family) must be run at corpus assembly time. Any cell with 0 samples where both marginals are >0 is a RED FLAG requiring remediation before training.

**Per-source contribution cap:** No single source dataset may contribute >40% of any class in any training dataset. This prevents a single dataset's labeling biases (quality, annotation conventions, domain) from dominating any learned class representation.

---

## §5 — Ideal Split Structure and Provenance Requirements

### Split Mechanics

The ideal corpus enforces a global split assignment that applies to all 22 heads simultaneously. This is the central architectural invariant, and it follows directly from the SigLIP 2 shared backbone: the backbone cannot have "seen" an image for one head and "not seen" it for another.

The split structure must satisfy these properties:

- **Primary key:** SHA256 hash of raw image file content (`corpus_id: "sha256:{64-char hex}"`). No image may appear under two different corpus_ids.
- **No cross-split collisions:** An image in `train` for head A cannot be in `test` for head B. The global split_type is the single authoritative split assignment for every head.
- **70/15/15 by source document ID:** Splits are computed on source document identifiers before any rotation, augmentation, or derived view is created. All derived views of the same source document inherit its split assignment.
- **Val/test immutability:** Once a record is assigned `val` or `test`, its split_type is sealed with a `val_immutable_since` or `test_immutable_since` timestamp. No process may change it. The integrity of val and test depends on this invariant.
- **Reserved pool:** Large source datasets are super-sampled at corpus construction time with the majority of records assigned `corpus_status: reserved`. Reserved records are the preferred source for future OOD expansion — they have never been seen by any training run, providing a clean boundary.
- **OOD is one-way:** Once a record is assigned `ood`, it cannot revert to `train` or `reserved`. Records promoted from `train` to `ood` carry a `promoted_to_ood_at` timestamp; models trained before this timestamp have seen the image and their OOD evaluation on it is informational rather than rigorous.
- **Near-duplicate exclusion:** pHash Hamming distance ≤5 against any active record triggers `corpus_status: excluded` with `exclusion_reason: near_duplicate`. No cross-dataset semantic duplicates in val or test.
- **Benchmark wall:** SmartDoc-QA, Q-Doc, and DIQA-5000 val/test splits are permanently reserved as benchmarks. These records may not appear in any training manifest.
- **OOD pre-designation:** OOD records must be designated before any training run begins. Post-training OOD promotion is permitted for failure mode discovery but carries the contaminated-boundary caveat (`ood_source: promoted_from_train`). The `_validate_manifest_no_ood()` function in `scripts/prepare_multitask_datasets.py` enforces this at manifest generation time.

### Provenance Requirements

Every sample in every training manifest must carry a `provenance` field. This field is mandatory — it is enforced at manifest generation time, not as a post-hoc annotation. Its value enables real/synthetic gap analysis, mixing cap enforcement, and audit of synthetic contribution by task.

| Provenance Value | Meaning | Primary Use |
|---|---|---|
| `real_scan` | Physical document scanned by flatbed or ADF scanner | Orientation (real component), Skew (natural scans), Capture (SCANNER_FLATBED/ADF) |
| `real_camera` | Physical document photographed by camera or smartphone | Capture (CAMERA classes), Shadow/Warping negatives, IQA camera component |
| `real_born_digital` | Born-digital PDF rendered to raster image | Orientation (real component), Resolution Quality, Capture (BORN_DIGITAL), IQA negatives |
| `real_paired` | Real document from a paired shadow/warping correction dataset | Shadow (sd7k, wsrd), Warping (anyphotodoc6300, warpdoc, docalign12k, docreal, drccbi) |
| `synthetic_v3` | Generated by synth-multiscript-v3 pipeline | Orientation (v3 non-Latin), Shadow (Augraphy overlay), Warping (perspective/curl/fold), Script (v3 component), Handwriting negatives |

---

## §6 — Label Quality Requirements

Label quality is expressed as a continuous training weight, not a binary accept/reject threshold. The tier system defines base weights; the actual `training_weight` for each sample is `tier_base_weight × min(confidence, 1.0)`. Samples with `confidence < 0.5` are excluded regardless of tier.

**Tier definitions:**

| Tier | `tier_base_weight` | Required For | Min Confidence | Acceptance Criteria |
|---|---|---|---|---|
| `tier_0_exact` | 1.0 | Synthetic ground truth (orientation rotation, skew angle, shadow Augraphy parameter, warping warp parameter, code generation) | 1.0 | Ground truth by construction; confidence is definitionally 1.0 |
| `tier_1_annotation` | 1.0 | IQA overall quality (human MOS), handwriting legibility (human assessment), shadow/warping paired GT | ≥0.9 | Human MOS SRCC ≥0.65 (overall quality); inter-annotator agreement documented |
| `tier_2_model` | 0.8 | IQA pseudo-labels (VLM), script labels from OpenLID on COCO-Text, shadow/warping severity from L2 model inference | ≥0.7 | VLM pilot SRCC ≥0.60 before scaling to full corpus; cross-validation with classical detector |
| `tier_3_heuristic` | 0.5 | Skew natural scan (Hough ensemble, conf≥0.7), capture method (ADF/FAX heuristic), handwriting content type (OCR-derived), resolution quality (CC analysis) | ≥0.5 | Cross-validator agreement documented; disagreement >threshold → reject, not uncertainty-label |

**Per-head minimum label tier (22 heads):**

- MNV4-H1 (orientation_cls): tier_0_exact (rotation by construction)
- MNV4-H2 (skew_reg): tier_0_exact for synthetic; tier_2_model (Hough+projection agreement) for natural scans
- MNV4-H3 (resolution_quality_reg): tier_0_exact for DPI renders; tier_3_heuristic for camera captures
- SIG-G1-1 through SIG-G1-6 (IQA 6 heads): tier_1_annotation for Phase 1 hard labels; tier_2_model for Phase 2 pseudo
- SIG-G2-1 (script_cls): tier_0_exact for v3; tier_1_annotation for MDIW13/SIW13; tier_2_model for OpenLID-derived
- SIG-G3-1 (orientation post-correction): tier_0_exact (same as MNV4-H1)
- SIG-G3-2 (skew post-correction): tier_0_exact for synthetic; tier_2_model for natural scans
- SIG-G4-1 (handwriting_presence_cls): tier_1_annotation for HierText/COCO-Text; tier_0_exact for negatives
- SIG-G4-2 (handwriting_legibility_cls): tier_1_annotation required; tier_3_heuristic weight cap 0.4–0.5
- SIG-G4-3 (handwriting_content_type_cls): tier_3_heuristic (OCR-derived), weight 0.4
- SIG-G4-4 (presence_reg): tier_1_annotation for area-ratio measurement; tier_3_heuristic cap 0.4
- SIG-G4-5 (legibility_reg): tier_1_annotation required for primary labels
- SIG-G5-1 (capture_method_cls): tier_1_annotation for source-native; tier_3_heuristic for ADF/FAX
- SIG-G5-2 (shadow_reg): tier_0_exact for v3 Augraphy; tier_1_annotation for sd7k/wsrd paired GT
- SIG-G5-3 (warping_reg): tier_0_exact for v3 transforms; tier_1_annotation for real paired GT
- SIG-G5-4 (code_cls): tier_0_exact for generated code images; tier_1_annotation for curated negatives
- SIG-G5-5 (resolution_quality_reg): same as MNV4-H3

**Label confidence floor:** >80% of samples must have confidence ≥0.6. Any dataset where >30% of samples have confidence <0.5 must be rejected or re-labeled before use.

**Mandatory N_A Handling (Group 4 Handwriting Heads):**

When a label is structurally not applicable to a sample (see §3.6), the training data record MUST carry:

- `label_value = -1.0` (sentinel value; NOT 0.0, NOT null)
- `masked_loss = true` (boolean flag)

The training loop implementation must skip loss computation for records with `masked_loss = true`.
This applies specifically to SIG-G4-2 (legibility_cls), SIG-G4-3 (content_type_cls), SIG-G4-4
(presence_reg), and SIG-G4-5 (legibility_reg) for samples where handwriting presence = NONE.

Violation: Using 0.0 instead of -1.0 for N_A is a **training defect** (P0). The model will learn
"printed document = zero legibility" which is semantically incorrect and will degrade Group 4 accuracy.

---

## §7 — Synth-Multiscript v3 as Multi-Task Backbone

Synth-multiscript-v3 is the single synthetic backbone from which multiple training dataset views are derived. Its pristine-base design — no degradation baked into the stored images, all parameters in paired sidecar JSON for reproducible replay — is what makes multi-task view derivation possible without information loss.

**Core design properties (as-built):**

- 190,485 JPEG quality 95 images across 27 ISO 15924 scripts (GCS-confirmed 2026-02-21 by live gsutil ls count; generator stopped at 190,485 due to per-script pool exhaustion bug — 350K was the target, not the actual count)
- 198 OpenLID-v2 language varieties; 198 languages
- Pristine storage: degradation parameters recorded in `generation_params.degradation_seed` for reproducible replay
- 7-tier DPI distribution: VERY_LOW 72 (8.1%), LOW 100 (11.9%), MEDIUM_LOW 150 (15.0%), MEDIUM 200 (20.1%), STANDARD 300 (24.8%), HIGH 400 (12.0%), VERY_HIGH 600 (8.0%)
- Quality tiers: PRISTINE 10%, HIGH 24.9%, MEDIUM 35%, LOW 20.1%, DEGRADED 9.9%
- Color modes: color 60%, grayscale 30%, binarized 10%
- Document age: modern 80%, aged 15%, historical 5%
- CJK vertical text (tategaki): Jpan 30.0%, Hans 10.0%, Hant 10.2% (validated)
- Geometric labels in sidecar: `orientation_class` (0/90/180/270), `skew_angle_degrees` (±22°)
- Resolution quality labels (v2.3): `character_height_px`, `coarse_bucket`, `resolution_quality_score`, `measurement_method: sauvola_cc_v2`
- IQA labels (8 dimensions): blur, noise, compression, ink_degradation, paper_degradation, geometric_distortion, bleed_through, overall_quality
- Split registry: `splits.jsonl` at GCS prefix root (SHA256-keyed, 345,638 entries)

**Known distribution issue:** Arab script has 49,169 images (3.8× the per-script target of 12,963); 17 scripts are below target. This is a confirmed generator bug. Weighted resampling is required before training use. Regeneration from scratch is not required — the base images are correct, only the sampling ratios need adjustment. Script composition also differs from the original design: Armn (Armenian) and Grek (Greek) replaced Cher (Cherokee) and Cans (Canadian Aboriginal Syllabics); Kore is used for Korean instead of Hang.

**Derived task-specific views:**

| View | Count Used | Selection | Transforms Applied | Label Source |
|---|---|---|---|---|
| Script Detection | ~60K (stratified, rebalanced) | All scripts with weighted resampling to hit class targets | None (pristine base used directly) | Script from folder label (tier_0_exact) |
| Orientation (synthetic component) | ~20K (non-Latin only) | 19 non-Latin scripts; Latin excluded | 0/90/180/270 rotation applied at derivation time | `orientation_class` from sidecar (tier_0_exact) |
| Skew (synthetic component) | ~10K | Stratified by script and DPI | Exact angle applied within ±10° range | `skew_angle_degrees` from sidecar (tier_0_exact) |
| Resolution Quality | ~5K | Stratified across all 7 DPI tiers | Char height measurement at pristine base | DPI + CC analysis (tier_0_exact) |
| IQA Phase 2 pseudo-labels | Up to 20K | Diverse subset across scripts and quality tiers | Degradation parameter replay from sidecar seed | Existing IQA labels in sidecar (tier_2_model at 0.8× weight) |
| Shadow synthetic | ~8K | Diverse subset; all 27 scripts | Augraphy shadow overlay (4 types: edge/cast/spotlight/scanner_lid) | Augraphy severity parameter (tier_0_exact, confidence 1.0) |
| Warping synthetic | ~5K | Diverse subset; all 27 scripts | Perspective/page_curl/fold transforms | Normalized warp parameter (tier_0_exact, confidence 1.0) |
| Capture Method | ~7.5K | Any subset | None | `capture_method = "synthetic"` (tier_0_exact) |
| Handwriting negatives | ~5K | Printed-only (non-handwriting font tiers) | None | NONE class (tier_0_exact) |

**Latin exclusion rule for orientation/shadow/warping:** Synthetic Latin documents must not contribute to the orientation, shadow, or warping derived views. Latin orientation is adequately covered by real documents; adding synthetic Latin to these views inflates the easy majority class without improving robustness to production inputs. Non-Latin scripts (19 scripts) provide the gap coverage these views need.

---

## §8 — Wild Condition Coverage Requirements

The following wild conditions must be represented in the corpus. The table shows requirement, source
dataset, required acquisition step, and current status. All 8 conditions must be confirmed before
training is marked production-ready.

**IQA Wild Conditions:**

| Condition | Requirement | Source Dataset | Acquisition Step | Status |
|---|---|---|---|---|
| Compound distortion ≥10% | ≥10% of IQA training set has ≥2 simultaneous distortions | Phase 1B compound sub-split (§3.4) | Assemble Phase 1B (blur+JPEG, blur+noise, noise+contrast+JPEG, shadow+blur, blur+skew+noise) | Not assembled |
| Mobile blur + defocus | Camera blur distinct from motion blur; defocus circles present | Phase 1C: MIDV500 + RealDAE camera subset | Verify blur_type labels in MIDV500 L2 metadata; filter for defocus | Not assembled |
| Book gutter shadow | Shadow gradient distinct from flat-document edge/cast shadows | Shadow dataset §3.8: requires sd7k severity labeling first | After L2 severity labeling: filter sd7k for shadow_type=book_gutter or add synthetic book_gutter via Phase 1 view scripts | Pending (Gap 5) |
| Aged yellowing / foxing ≥10% | ≥10% of IQA samples with document_age=aged or historical | v3 backbone (15% aged, 5% historical); RealDAE | Verify v3 IQA view uses document_age-diverse source images | Pending |
| Fax halftone | Screening artifacts distinct from JPEG blockiness | Capture method dataset §3.7: FAX class ≥2,500 samples | Acquire or simulate fax halftone documents; include in IQA cross-tabulation | Pending |
| Screen recapture moiré | RGB subpixel aliasing from photographing a screen | OOD-Capture §3a; IQA cross-tab | Internal photography of LCD/OLED screens; include ≥200 in IQA compound sub-split | Pending |

**Script Wild Conditions:**

| Condition | Requirement | Source Dataset | Acquisition Step | Status |
|---|---|---|---|---|
| Historical typography (Fraktur/Ottoman) ≥5% | ≥5% of script training with document_age=historical | MDIW13 (partial); OOD-Script 1e/1f | Verify MDIW13 historical subset; add OOD-Script historical samples | Pending |
| Degraded script samples ≤70% per class | Each class ≤70% pristine/high quality | v3 backbone quality distribution | v3 has 65% HIGH/PRISTINE — verify no single class exceeds 70% pristine | Pending (verify) |

**Orientation / Skew Wild Conditions:**

| Condition | Requirement | Source Dataset | Acquisition Step | Status |
|---|---|---|---|---|
| Symmetric documents ≥2% | ≥2% orientation samples with orientation_ambiguous=true | Orientation dataset §3.1 | Blank pages, figure-only, symmetric grids — filter DocLayNet for sparse-text pages | Pending |
| Skew + warping ≥5% | ≥5% of skew samples with simultaneous warping_severity > 0.2 | Skew dataset §3.2 | Cross-tabulate skew set with warping labels; add anyphotodoc6300 skewed subset | Pending |

**Handwriting Wild Conditions:**

| Condition | Requirement | Source Dataset | Acquisition Step | Status |
|---|---|---|---|---|
| All 5 script families | Arab, CJK, Devanagari, Latin, other scripts all present | KHATT (Arab), CASIA-HWDB (CJK), IIIT-INDIC (Deva), IAM (Latin) | P0 prerequisites: acquire KHATT, CASIA-HWDB, IIIT-INDIC, HKR | Blocked (P0 prereqs) |
| ILLEGIBLE ≥5% | ≥5% of handwriting samples in ILLEGIBLE class | §3.6 ILLEGIBLE acquisition plan | See §3.6 ILLEGIBLE Class Acquisition Plan | Pending |
| Mid-range presence ≥20% | ≥20% of samples with handwriting_presence_score 0.2–0.7 | Handwriting dataset §3.6 | Verify SPARSE/MODERATE class distribution in assembled dataset | Pending |

**Page Attribute Wild Conditions:**

| Condition | Requirement | Source Dataset | Acquisition Step | Status |
|---|---|---|---|---|
| Modern CIS scanner ≥1,500 | ≥1,500 SCANNER_FLATBED samples from modern CIS (2010+) hardware | Capture method §3.7 | MIDV-2020+ or MIDV500 for modern flatbed; verify scanner vintage metadata | Pending (Gap 8) |
| ADF curl artifacts | ADF-specific curl artifacts present in warping training | Warping §3.9 + Capture §3.7 | Internal scanning with Fujitsu ScanSnap (ADF); label warping_type=page_curl | Pending |
| Vector PDF DPI paradox | Model must NOT flag low-DPI vector PDFs for upscaling | Resolution quality §3.3: confound sub-dataset | Assemble confound sub-dataset: DocLayNet PDFs rendered at 72/150/300 DPI | Pending |

---

## §9 — What the Corpus Explicitly Excludes

The corpus boundary is as important as its contents. The following are explicitly out of scope, and data or labels addressing these concerns must not be added to training manifests:

**Permanently reserved scripts (OOD-only):** Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) are permanently excluded from all training manifests. These three scripts serve as OOD anchors for evaluating open-set rejection and script generalization. They must not appear in training even after future OpenLID expansion phases. The `_validate_no_reserved_scripts()` guard in `scripts/prepare_multitask_datasets.py` enforces this at manifest generation time and is not optional.

**Irrecoverable physical damage:** Documents with tears removing content, complete occlusion from physical debris, burned or water-damaged beyond character recognition, or permanent chemical degradation are excluded. These cannot be corrected by the pipeline and should be rejected at intake rather than trained on.

**Statistical and model-level problems:** Language model mismatch (OCR vocabulary gaps for rare languages), confidence drift from production distribution shift, and ensemble disagreement calibration are monitoring concerns, not training data problems. These are addressed by the monitoring and drift detection system (Phase 6), not by adding training samples.

**Semantic and layout problems requiring discourse understanding:** Reading order prediction, cross-page reference resolution, document section coherence, and table-of-contents mapping are out of scope for Project A and are the responsibility of the Unify (foundry-unify) and Chunk (foundry-chunk) projects in the RAG pipeline.

**Pipeline self-inflicted artifacts:** Double JPEG compression from intermediate processing steps, border padding from incorrect image resizing, and color space conversion artifacts from incorrect channel handling are engineering bugs, not training data gaps. These must be fixed in the pipeline rather than trained around.

**Benchmark test splits (benchmark wall):** SmartDoc-QA val/test, Q-Doc val/test, and DIQA-5000 val/test are permanently excluded from training manifests. These provide the independent held-out evaluation that validates production readiness. The benchmark wall must hold: no training sample may originate from these benchmark splits.

---

## §10 — Corpus Verification Framework

### §10.1 Pre-Training Assembly QA

The following checks must pass before any training run begins. Failures are not warnings — they are blockers.

| Check | Method | Threshold | Red Flag → Action |
|---|---|---|---|
| Class balance | Chi-square vs target distribution | p > 0.01 | Any class <50% of target → add samples or adjust weights |
| Split leakage | Set intersection on source document IDs across all datasets | 0 overlap | ANY overlap → HALT, rebuild split |
| Global split consistency | SHA256 lookup across all training tasks | Same image in same split everywhere | Same image in `train` for task A and `test` for task B → HALT |
| Label confidence | Histogram of confidence scores per dataset | ≥80% above 0.6 | >30% below 0.5 → re-label or exclude dataset |
| Capture method coverage | Count per capture type in applicable datasets | ≥minimum thresholds from §3 | Any mandatory type at 0 → block training |
| Script class coverage | Count per ML class in script dataset | ≥5,000 per class | Any class <100 samples → HALT script head training |
| Resolution spread | KS test for uniformity across 7 DPI tiers | p > 0.05 | Clustered at single DPI → re-sample |
| Image integrity | PIL.Image.verify() on all training images | 0 corrupt files | Any corrupt → exclude and replace |
| Near-duplicate detection | pHash Hamming distance ≤5 across val/test | <1% near-duplicates in val/test | >5% near-duplicates → deduplicate |
| Per-source contribution cap | Count per source per class | No single source >40% of any class | Violation → downsample offending source |
| OOD leakage | `_validate_manifest_no_ood()` against `ood_registry.jsonl` | 0 OOD records in training manifests | Any OOD record in train → HALT |

### §10.2 Script × Degradation Cross-Tabulation (Mandatory)

For each cell in the (script_family × degradation_type) matrix, the ideal corpus must contain ≥100 training samples with severity >0.3. Different scripts have fundamentally different tolerance profiles for each degradation type (Arabic is more sensitive to stroke blur; CJK is more sensitive to low-contrast; Devanagari requires higher stroke width for component legibility). Training a head on a corpus with zero samples in any cell produces systematic bias on that (script, degradation) combination.

Training must HALT if any cell is 0 after corpus assembly.

| script_family | blur | noise | contrast | compression | shadow | warping |
|---|---|---|---|---|---|---|
| Latin | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required |
| Arabic | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required |
| CJK | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required |
| Devanagari | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required |
| Cyrillic | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required | ≥100 required |

Verification must be added to `scripts/verify_dataset_diversity.py` (or equivalent corpus QA script). The cross-tabulation result must appear as a table in the pre-training QA report.

### §10.3 Known Cross-Dataset Issues (KI-001 to KI-009)

The Layer 2 audit identified 9 systemic quality issues affecting multiple datasets. All must be resolved or explicitly accepted with documented rationale before training begins.

| KI | Severity | Issue | Fix |
|---|---|---|---|
| KI-001 | CRITICAL | Docling layout label casing mismatch across all 52 Docling-processed datasets | `scripts/standardize_layout_labels.py` (automated) — run before any manifest generation |
| KI-002 | HIGH | Docling Table detection unreliable on multi-column text pages | Manual VLM verification required before using layout `has_tables` field from affected datasets |
| KI-003 | MEDIUM | Docling Picture detection unreliable on dense text pages | Manual VLM verification required before using layout `has_figures` field from affected datasets |
| KI-004 | HIGH | LLM handwriting detection unreliable on synthetic documents | Override pattern: set `has_handwriting=False` for all synthetic dataset records; do not use LLM-derived handwriting labels on v3 |
| KI-005 | HIGH | LLM cannot detect synthetic capture method (all produces "born_digital" or UNK) | Override pattern: set `capture_method=synthetic` for all v3 and DocSynth300K records |
| KI-006 | MEDIUM | LLM formula detection over-flags scientific text (text with Greek letters classified as formula) | Manual VLM verification required before using `has_formula` field from scientific domain datasets |
| KI-007 | LOW | LLM domain classification high UNK rate on generic/narrative content | Accepted limitation (taxonomy limitation for non-domain-specific text); UNK is a valid domain label |
| KI-008 | LOW | Nepali handwritten label noise from character variant ambiguity | Dataset-specific mitigation: apply 0.8× weight on Nepali Handwritten labels for legibility head |
| KI-009 | MEDIUM | Latin language conflation in MLT19 and COCO-Text (fr/de/it mapped to en) | Mitigated by LLM refinement — resolves 1,731/2,671 conflated samples; accept residual uncertainty on remaining 940 |

### §10.4 Training Monitoring

The ideal corpus, once assembled, must produce training runs that exhibit the following monitoring properties. These thresholds define what healthy training looks like; deviations trigger investigation.

| Metric | Frequency | Threshold | Action on Violation |
|---|---|---|---|
| Per-class val accuracy | Every epoch | No class drops >5% from peak across 3 consecutive epochs | Increase class weight for underperforming class |
| Rare script accuracy (Tibetan, Hebrew) | Every epoch | ≥70% accuracy | Add more synthetic data for that script; consider 5-fold CV |
| Synthetic vs. real accuracy gap | Every 5 epochs | <10% gap for classes with >50% synthetic training data | Reduce synthetic weight; investigate domain shift |
| Per-capture-method accuracy | Every epoch | No capture type >5% below average | Investigate capture-specific failure mode |
| Gradient norm per task group | Every batch | No task group >5× average across 10 batches | Check PCGrad implementation; verify Kendall uncertainty weighting |

### §10.5 Red Flags That Halt Training

Training must halt immediately upon detection of any of the following conditions:

1. **Split leakage detected:** SHA256 collision between train and val/test for any head — halt all training runs immediately and rebuild the split registry.
2. **Class collapse:** Any class achieves <50% accuracy for 5 consecutive epochs despite weight adjustment — corpus may be mislabeled for that class; investigate before continuing.
3. **Label noise >5%:** >5% of samples flagged as likely mislabeled by cross-validator — re-label the affected subset before continuing.
4. **Synthetic-real accuracy gap >15%:** For classes with >50% synthetic training data — synthetic distribution does not match production distribution; reduce synthetic weight or add real data.
5. **Missing critical dimension:** 0 samples for any category flagged as CRITICAL in §3 diversity tables — the head will fail systematically on that category in production.
6. **Confidence floor violation:** >30% of labels in any dataset have confidence <0.5 — the dataset's labels are unreliable; exclude or re-label before use.

---

## Gap Registry

> **Source**: `docs/planning/CORPUS_OOD_REVIEW_REPORT.md` (2026-02-23, 5-model consensus)
> **Overall verdict**: ❌ NOT READY FOR PHASE 2 TRAINING — 6 of 11 acceptance criteria fail; 2 at risk
> **Minimum condition to begin training**: P0-1, P0-2, P0-3, P0-4, P0-5, P0-6 resolved; P0-7 has a defined scaling decision

### P0 — Blockers (must resolve before Phase 2 training)

| Gap ID | Priority | Dataset / Head | One-Line Description | Acceptance Criterion |
|--------|----------|---------------|----------------------|----------------------|
| P0-1 | P0 | SIG-G3-2 | Separate ±2° narrow-range dataset (~20K images) required for post-correction skew | Narrow-range dataset assembled and split registry updated |
| P0-2 | P0 | SIG-G1-4 / MNV4-H2 | Label conflict: IQA skew_score and geometric skew_reg share the same label source but are different constructs | Derivation method for skew_score defined (Option A/B/C from review report §A5); no shared labels in multi-task training spec |
| P0-3 | P0 | IQA / SIG-G1-6 | VLM SRCC decision tree missing — no halt/fallback conditions defined before scaling pseudo-labels to 2–5K | Decision tree documented; prompt v2.0 validated on 30–50 images; SRCC result recorded in provenance |
| P0-4 | P0 | SIG-G4-2 / SIG-G4-5 | ILLEGIBLE class void — 0 ILLEGIBLE handwriting samples across all datasets | ≥5,000 ILLEGIBLE samples acquired and confirmed in handwriting manifest |
| P0-5 | P0 | SIG-G5-2 / SIG-G5-3 | L2 severity labels required for shadow and warping — `label_shadow_severity.py` and `label_warping_severity.py` must run on GPU VM | Both scripts executed; L2 JSON updated; real records > 0 confirmed in `prepare_multitask_datasets.py shadow` and `warping` dry-runs |
| P0-6 | P0 | SIG-G2-1 | Arab script 3.8× imbalance violates §2 max 3× constraint — 49K images vs. ~13K budget | Arab capped at ≤13K (or ≤3× minimum class); `prepare_multitask_datasets.py script` dry-run confirms no class >3× min |
| P0-7 | P0 | SIG-G1-1 to SIG-G1-5 | IQA Phase 1A undersized — 16.3K vs. 50–100K industry standard for 101M-parameter model with 6 concurrent heads | Scaling path defined (decision doc or GitHub issue); either more OHR-Bench labels or VLM expansion plan recorded |
| P0-8 | P0 | OOD-Mixed | OOD-Mixed 9a-1 (orientation cascade, 100 images) and 9a-2 (skew cascade, 100 images) re-prioritized to P0 | Both sub-sources derived from existing labeled data and added to OOD catalog with sample counts |
| P0-9 | P0 | OOD-Domain | OOD-Domain smoke test (100 ArXiv PDFs) re-prioritized to P0 | 100 ArXiv PDFs acquired, labeled for all 22 heads, and added to OOD-Domain sub-source |
| P0-10 | P0 | OOD (all) | Open-set rejection must use temperature scaling + Energy Score — entropy ≥0.7 threshold is uncalibrated and insufficient for SigLIP 2 | Temperature scaling calibrated on held-out val; Energy Score (LogSumExp) replaces raw softmax entropy in OOD evaluation pipeline |

### P1 — Required before final model release

| Gap ID | Priority | Dataset / Head | One-Line Description | Acceptance Criterion |
|--------|----------|---------------|----------------------|----------------------|
| P1-1 | P1 | SIG-G5-1 | CamScanner 8th capture class missing — mobile-processed docs silently misclassified into existing 7 classes | Either 8th class added to SIG-G5-1 with training samples, OR explicit abstention mechanism documented and tested |
| P1-2 | P1 | §8 Wild Conditions | Wild conditions §8 missing 6 production scenarios: redaction bars, CamScanner, stamps/seals, photocopy chains, fax artifacts, mixed-language pages | All 6 scenarios added to §8; training data acquisition plan documented for each |
| P1-3 | P1 | OOD (all) | OOD total scale-up to ~12,000–15,000 images OR formal "directional-only" declaration | Either OOD catalog scaled to ≥12K, OR governance document signed declaring all OOD results directional-only until scaling complete |
| P1-4 | P1 | OOD-Mixed | MNV4-H3 → SigLIP resolution cascade failure path not covered in OOD-Mixed | New OOD-Mixed sub-source added testing MNV4-H3 misclassification → SigLIP blurry input scenario |
| P1-5 | P1 | OOD-Mixed | Clean-But-Novel false positive scenario missing — OOD-Mixed does not test clean novel documents causing false MNV4 corrections | New OOD-Mixed sub-source (~100 clean novel-layout images) added; false positive rate measured |
| P1-6 | P1 | SIG-G4-2 / OOD-Handwriting | ILLEGIBLE OOD floor of 65% is unrealistic given 0 training samples | OOD floor for ILLEGIBLE recalibrated to 40% with explicit class-void flag in OOD catalog |
| P1-7 | P1 | OOD-Resolution | Hybrid vector/raster PDF scenario missing from OOD-Resolution | 100–200 hybrid PDF samples added to OOD-Resolution |
| P1-8 | P1 | OOD-Degradation | Albumentations not formally committed as Phase 4 augmentation engine in OOD_DATASET_CATALOG.md | OOD_DATASET_CATALOG.md updated to mandate Albumentations for Phase 4; Augraphy banned for OOD-Degradation |
| P1-9 | P1 | §7 / Script | v3 shared-backbone correlated failure risk not documented | Risk note added to §7 (or §12) documenting that 7/10 training datasets share the v3 rendering pipeline |
| P1-10 | P1 | SIG-G4-3 | content_type labeling uses OCR confidence as proxy for legibility — circular dependency | OCR-independence requirement defined in label spec; alternative labeling strategy documented |
| P1-11 | P1 | OOD-Geometry | Monolithic orientation floor 80% masks two fundamentally different failure modes | OOD-Geometry evaluation split into Abstention-Rate (≥85%) and Correction-Accuracy (≥88%) metrics |
| P1-12 | P1 | OOD (new) | OOD-Composite category proposal not evaluated — 300 images targeting compound edge cases spanning multiple failure modes | Feasibility assessment completed; either 10th OOD category added or explicitly deferred with rationale |

### P2 — Improvements for V2

| Gap ID | Priority | Dataset / Head | One-Line Description | Acceptance Criterion |
|--------|----------|---------------|----------------------|----------------------|
| P2-1 | P2 | OOD (all) | ODIN (temperature scaling + input perturbation) not implemented for open-set rejection | ODIN implemented and benchmarked against Energy Score on reserved scripts |
| P2-2 | P2 | OOD (all) | Mahalanobis distance on feature embeddings not implemented for reserved script detection | Mahalanobis distance scorer implemented; class mean embeddings stored from training |
| P2-3 | P2 | OOD (all) | Active learning not integrated for OOD sampling to reduce total images needed | Active learning pipeline prototype evaluated; total OOD image reduction estimate documented |
| P2-4 | P2 | SIG-G3-2 | Dedicated ±0.5° ultra-narrow dataset for sub-degree post-correction precision not assembled | ±0.5° dataset assembled; MAE improvement vs. ±2° dataset measured on validation set |
| P2-5 | P2 | Resolution Quality | Resolution Quality V2 algorithm (Sauvola + projection profiles) not applied to v3 images | V2 algorithm run on v3 sample; IQR improvement vs. V1 (9.0px → target 3–4px) measured and recorded |

---

## §11 — Corpus Acceptance Criteria

> **Review verdict (2026-02-23)**: ❌ FAIL — 6 of 11 criteria fail; 2 at risk. Corpus is NOT READY FOR PHASE 2 TRAINING.
> See `docs/planning/CORPUS_OOD_REVIEW_REPORT.md` for full blocker analysis.

An assembled corpus is acceptable for training when ALL of the following checkboxes pass. No partial credit.

- ❌ **FAIL** Each head has ≥ minimum training samples at the required label tier, as specified in §2. **Blocker: P0-7 (IQA 16.3K vs. 50–100K), P0-1 (SIG-G3-2 no narrow-range dataset), P0-4 (ILLEGIBLE class void)**
- ⚠️ **AT RISK** No synthetic mixing cap violated: orientation ≤40%, source ≤5%, shadow ≤50%, warping ≤30%, script ≤60% (from `SYNTHETIC_CAPS` in `scripts/prepare_multitask_datasets.py`). **Risk: P1-9 (v3 shared-backbone correlated failure not documented)**
- [ ] Global split registry: SHA256 primary key with no collision between train, val, test, and ood
- [ ] All 14-dimension minimum thresholds met (§4 minimums passed for applicable dimensions per dataset)
- [ ] No reserved scripts (Mongolian/Mong, Syriac/Syrc, Georgian/Geor) present in any training manifest
- [ ] Val and test immutability sealed with `val_immutable_since` and `test_immutable_since` timestamps
- [ ] OOD registry populated and `_validate_manifest_no_ood()` passing before first training run
- ❌ **FAIL** Wild condition requirements met for each head group: compound IQA sub-split assembled, multi-column ≥20% of skew set, ambiguous orientation class labeled, all 5 handwriting script families present, modern CIS flatbed ≥1,500, book spine warping samples present (§8). **Blocker: P1-2 (6 wild condition scenarios missing)**
- ❌ **FAIL** Label confidence floor: >80% of samples in every dataset have confidence ≥0.6. **Blocker: P0-3 (VLM SRCC 0.53 — gate not met; no halt condition defined)**
- [ ] Provenance field present on every sample in every training manifest
- ⚠️ **AT RISK** Script × degradation cross-tabulation: ≥100 samples per cell for all 30 cells in 5×6 matrix (§10.2). **Risk: 12 shadow/warping/compound cells blocked on GPU generation runs (review §A4)**
- [ ] All 9 KI issues resolved or explicitly accepted with documented rationale (§10.3)
- ❌ **FAIL** IQA compound distortion sub-split (3–5K) assembled as separate held-out eval (not folded into val/test). **Blocker: Phase 1B sub-split not yet assembled**
- ❌ **FAIL** v3 rebalancing complete: Arab class downsampled from 49,169 to ≤3× target; 17 under-target scripts upweighted via sampling strategy. **Blocker: P0-6 (Arab 3.8× violates §2 constraint)**
- ❌ **FAIL** Shadow and warping have real data assembled. **Blocker: P0-5 (0 real records; `label_shadow_severity.py` and `label_warping_severity.py` not yet run)**

---

## §12 — Current State vs Ideal (Gap Summary)

> **Note**: The naive per-head sum (~565K) overstates the actual unique image requirement.
> Cross-dataset sharing reduces the true unique image footprint to **~420-440K**. See §1b
> for the detailed sharing analysis and source pool breakdown.

The table below shows the delta between the ideal corpus specification and the current assembly state as of 2026-02-23. Priority P0 gaps block training; P1 gaps allow training to begin on completed heads while the gap is resolved.

| Dataset | Ideal Size | Current State | Key Gap | Priority |
|---|---|---|---|---|
| orientation | 50,000 | 50K (old config, predominantly Latin) | Rebuilding as hybrid (Stream 4C scripts complete, execution pending); non-Latin <1%; `orientation_ambiguous` class not yet labeled | P0 (Stream 4C) |
| skew | 90,000 | 90,412 (train 70,763 / val 9,025 / test 10,624) ✅ | conf≥0.7 filter excludes hardest multi-column samples; Gap 7 multi-column label quality gate present but not verified at scale | Complete |
| resolution-quality | 30,000 | ~5,499 labeled from DIQA-5000 only | V2 Sauvola+projection algorithm needed for precision <5px; OHR-Bench (8.5K) and RealDAE (1.2K) pending; confound sub-dataset (~2K) not yet assembled | P0 |
| iqa | ~25K hard + 100K pseudo | ~25K hard (Phase 1 complete) | Phase 1B compound sub-split (3–5K) not yet assembled; VLM bottleneck for overall_quality labels (SRCC 0.53, target 0.65); Phase 2 pseudo not yet assembled | P0 |
| script-detection | 108K balanced | 190,485 GCS-confirmed (generator stopped at 190K due to bug; 350K was target only); severely imbalanced: Arab 3.8× at 49K images vs. ~13K budget, 17 scripts below target | Weighted resampling required before any training use; v3 also needs Latin exclusion rule applied for orientation/shadow/warping views. **⚠️ CONSTRAINT VIOLATION: Arab script at 3.8× target (49K images vs. ~13K budget). Cap Arab at ≤13K images and redistribute budget to the 17 scripts below their floor before training.** | P0 |
| handwriting | 60,000 | 38,967 records (dry-run 2026-02-21; dry-run ≠ assembled — actual dataset not yet generated); only Latin/Arabic/Devanagari covered | KHATT, CASIA-HWDB, IIIT-INDIC, HKR not yet acquired (P0 prerequisites); ILLEGIBLE class void (0 samples — hard blocker). **⚠️ P0 SENTINEL DEFECT: N_A values must be encoded as -1.0 (with masked loss during training), NOT 0.0 (which maps to 'illegible' and corrupts regression heads G4-2 and G4-5). This must be resolved in label schema before assembling the handwriting dataset.** | P0 |
| capture-method | 50,000 | 39,893 records in source sub-command output; note 3 classes near-zero: CAMERA_PROFESSIONAL, FAX, and SCANNER_ADF each well below minimum targets | ADF heuristic labeling pending (manual verification of 100 samples required); FAX heuristic labeling pending; modern CIS flatbed ≥1,500 gap (Gap 8) unresolved | P1 |
| shadow | ~18,000 | 0 assembled (`label_shadow_severity.py` not yet run; 0 real records) | Generation scripts complete (`generate_v3_shadow_view.py`, `prepare_multitask_datasets.py shadow`); L2 `shadow_severity` annotation on sd7k/wsrd pending (GPU VM execution required); book gutter gap (Gap 5) unresolved | P1 |
| warping | ~24,000 | 0 assembled (derivation formula undefined; `label_warping_severity.py` not yet run; 0 real records) | Generation scripts complete (`generate_v3_warping_view.py`, `prepare_multitask_datasets.py warping`); L2 `warping_severity` annotation on anyphotodoc6300/warpdoc/docalign12k pending (GPU VM execution required) | P1 |
| code-detection | 10,000 | 8,613 dry-run (dry-run ≠ assembled — actual image generation not yet executed) | Generation script complete (`generate_code_detection_dataset.py`, 8,613 dry-run records); actual image generation on GPU VM pending; Playwright/carbon-now-cli renders not yet produced. **⚠️ P0 ARCHITECTURAL FIX APPLIED: head renamed from `code_reg` to `code_cls` in this document — also rename in `modal/train_siglip2_multitask.py`, head registry, and inference scripts** | P1 |

---

*This specification is authoritative for the unified training corpus. For implementation details — how to assemble each dataset, which scripts to run, and in what order — see `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md`, `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`, and the Stream 4C handoff documentation in `docs/handoff/SYNTH_MULTITASK_DIVERSITY_HANDOFF.md`.*

*Source references: `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`, `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md`, `docs/datasets/training/synth-multiscript-v3.md`, `docs/schema/corpus_manifest_v1.schema.json`, `scripts/prepare_multitask_datasets.py`.*
