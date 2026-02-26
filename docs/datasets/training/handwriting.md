---
l4_category: training-dataset
l4_dataset: handwriting
l4_workstream: WS3
l4_source_datasets:
  - hiertext
  - coco-text
  - iam
  - muharaf
  - nist-sd19
  - pucit-ohul
l4_generation_script: scripts/harmonize_handwriting_labels.py
l4_image_count: 60000
l4_status: blocked
---

# Handwriting Training Dataset

> ❌ **P0 BLOCKED — 17 open gaps across 5 heads**
> Status: 38,967 records dry-run (2026-02-21). Actual dataset: 0 assembled.
> Training BLOCKED until N_A sentinel defect resolved (see below).
>
> **Quick Stats**: 60,000 images (target) | 5 heads across 3 classification + 2 regression tasks | Multi-label
>
> **Status**: ❌ Blocked | **HAR Scores**: G4-1: 32/100, G4-2: 21/100, G4-3: 25/100, G4-4: 26/100, G4-5: 14/100 | **P0 Gaps**: 17 total across all 5 heads

---

## HAR Assessment (5-Model Consensus Review, 2026-02-21)

| Head | HAR Score | Grade |
|------|-----------|-------|
| G4-1 handwriting_presence_cls | 32/100 | Needs Work |
| G4-2 handwriting_legibility_cls | 21/100 | Needs Work |
| G4-3 handwriting_content_type_cls | 25/100 | Needs Work |
| G4-4 handwriting_presence_reg | 26/100 | Needs Work |
| G4-5 handwriting_legibility_reg | 14/100 | Blocked |

Average: ~24/100

---

## ⚠️ BLOCKING DEFECT: N_A Sentinel Encoding

**Defect**: N_A (not applicable / handwriting absent from this page) is currently
encoded as 0.0. This is WRONG and corrupts training.

- 0.0 in regression heads (G4-2 legibility, G4-5 legibility_reg) means "illegible"
- N_A must be encoded as **-1.0** with masked loss during training
- Using 0.0 conflates "no handwriting present" with "handwriting is illegible"
- This corrupts ALL 5 heads simultaneously

**Required fix**:

- Update label schema: N_A → -1.0
- Update label generation scripts to output -1.0 for absent-handwriting pages
- Update training loop: apply mask where label == -1.0; exclude from loss computation
- Verify: presence_reg head output for all-printed pages must cluster near 0.0, not -1.0

---

## ILLEGIBLE Class Gap (P0)

Current training examples for ILLEGIBLE class: **0**
Required: ≥5,000 examples

The ILLEGIBLE class requires samples where handwriting IS present but cannot be read
(heavily degraded, extreme stylization, water damage, faded ink).

**Acquisition blockers**:

| Dataset | Status | Note |
|---------|--------|------|
| KHATT (Arabic cursive) | ⏳ Pending acquisition | Public dataset; download required |
| CASIA-HWDB (CJK handwriting) | ⏳ Access request pending | 2–4 week approval process |
| IIIT-INDIC (Devanagari) | ⏳ Pending acquisition | Public access |
| HKR (Kazakh/Russian cursive) | ⏳ Pending acquisition | Public access |

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `handwriting` |
| **Head(s) Fed** | SIG-G4-1 `presence_cls`, SIG-G4-2 `legibility_cls`, SIG-G4-3 `content_type_cls`, SIG-G4-4 `presence_reg`, SIG-G4-5 `legibility_reg` |
| **Model(s)** | SigLIP 2 NAFlex |
| **Task Type** | Multi-label: 3 classification heads + 2 Gaussian NLL regression heads |
| **Primary L2 Field(s)** | `handwriting_assessment.presence` (5-class enum), `handwriting_assessment.legibility` (6-class enum), `handwriting_assessment.content_type` (7-class enum), `handwriting_assessment.presence_score` (float 0–1), `handwriting_assessment.legibility_score` (float 0–1) |
| **Training Phase** | Phase 3 — Handwriting |
| **Target Size** | 60,000 images |
| **Image Size** | Variable (source-native; normalized during assembly) |
| **Storage Location** | `E:\image_detection\03_training_datasets\handwriting\` |
| **GCS Path** | `gs://image_detection_b/handwriting_training/` (not yet populated) |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py handwriting` (subcommand not yet implemented) |
| **HAR Files** | [sig-g4-presence-cls.md](../../planning/har/sig-g4-presence-cls.md), [sig-g4-legibility-cls.md](../../planning/har/sig-g4-legibility-cls.md), [sig-g4-content-type-cls.md](../../planning/har/sig-g4-content-type-cls.md), [sig-g4-presence-reg.md](../../planning/har/sig-g4-presence-reg.md), [sig-g4-legibility-reg.md](../../planning/har/sig-g4-legibility-reg.md) |
| **DDR File** | [diversity_reports/handwriting_ddr.md](../diversity_reports/handwriting_ddr.md) |

### Head Specifications

| Head ID | Head Name | Task | Classes / Range | Performance Target |
|---------|-----------|------|-----------------|-------------------|
| SIG-G4-1 | `presence_cls` | Classification | 5 classes: NONE / MARGINAL / PARTIAL / SUBSTANTIAL / DOMINANT | Macro F1 ≥ 0.78 |
| SIG-G4-2 | `legibility_cls` | Classification | 6 classes: N_A / ILLEGIBLE / POOR / FAIR / GOOD / EXCELLENT | Macro F1 ≥ 0.60 (revised from 0.72; IAA ceiling) |
| SIG-G4-3 | `content_type_cls` | Classification | 7 classes: N_A / PRINTED / TYPED / HANDWRITTEN_CURSIVE / HANDWRITTEN_BLOCK / MIXED_PRINTED_HW / MIXED_TYPED_HW | Macro F1 ≥ 0.72 |
| SIG-G4-4 | `presence_reg` | Regression (Gaussian NLL) | 0.0–1.0 (area ratio) | Pearson r ≥ 0.80 + MAE ≤ 0.10 on mid-range holdout |
| SIG-G4-5 | `legibility_reg` | Regression (Gaussian NLL) | 0.0–1.0 (0 = illegible, 1 = perfect) | Pearson r ≥ 0.55 vs human MOS (revised from 0.80; IAA ceiling) |

All five heads are trained on the same 60,000-image dataset. Each image carries all five labels simultaneously. The `presence_cls` output is the gate for all secondary heads: when `presence = NONE`, all of `legibility_cls`, `content_type_cls`, `legibility_score`, and `presence_score` receive the **-1.0 N_A masked sentinel** (task_mask=0 → MultiTaskLoss skips these samples). Using 0.0 as the sentinel is the Defect 1 bug — corrected in harmonize_handwriting_labels.py.

---

## Section 2 — Status

| Metric | Value |
|--------|-------|
| **Assembly Status** | ❌ Blocked — 17 P0 gaps across 5 heads; no labels exist for any head |
| **Current Count** | 0 / 60,000 assembled (dry-run produced 38,967 records with binary labels only, not 5-class) |
| **HAR Adequacy Score (G4-1)** | 32/100 — ❌ Blocked |
| **HAR Adequacy Score (G4-2)** | 21/100 — ❌ Blocked |
| **HAR Adequacy Score (G4-3)** | 25/100 — ❌ Blocked |
| **HAR Adequacy Score (G4-4)** | 26/100 — ❌ Blocked |
| **HAR Adequacy Score (G4-5)** | 14/100 — ❌ Blocked (lowest of all 22 SigLIP 2 heads) |
| **P0 Gap Count** | 17 total (5 G4-1 + 4 G4-2 + 6 G4-3 + 4 G4-4 + 6 G4-5; some shared) |
| **Primary Blocker** | N_A sentinel defect (must fix before all labeling); 5-class label conversion not implemented in `harmonize_handwriting_labels.py`; `handwriting` subcommand of `prepare_multitask_datasets.py` not implemented; ILLEGIBLE class has zero training examples; MIXED_PRINTED_HW and MIXED_TYPED_HW classes have near-zero natural examples |
| **Estimated Unblock Effort** | 8–12 weeks (G4-1 through G4-3 dependencies are serial; G4-4 and G4-5 add regression-specific work on top) |
| **Last HAR Updated** | 2026-02-23 |

### Critical Prerequisite: N_A Sentinel Defect

**This must be fixed before any labeling or assembly runs begin.**

The scaffold for `legibility_score` and `presence_score` uses `0.0` as the sentinel value for N_A (no handwriting present). This is wrong. The correct sentinel is `-1.0` with masked loss (loss weight = 0 for N_A images). Using `0.0` would train the model to output near-zero scores for every printed page with no handwriting, conflating "absent handwriting" with "completely illegible handwriting." This defect propagates to every assembly script, every manifest schema, and every training manifest that references these two regression fields. It must be corrected in all locations before any manifests are generated.

---

## Section 3 — Source Pool Analysis

All five G4 heads draw from the same 60,000-image pool. Labels differ per head, but the underlying image set is shared. The label derivation strategy varies by head and source dataset.

### Label Derivation Strategies

| Strategy | Applicable Datasets | Heads Fed |
|----------|---------------------|-----------|
| `all_handwritten` | IAM, Muharaf, PUCIT-OHUL, NIST-SD2 — entire corpus is handwriting | G4-1 (DOMINANT), G4-4 (score ~0.90–1.0), G4-5 (EXCELLENT range) |
| `all_printed` | DocLayNet, TableBank, RVL-CDIP — born-digital or purely printed | G4-1 (NONE), G4-2 (N_A), G4-3 (N_A / PRINTED), G4-4 (score 0.0) |
| `model_derived` | HierText, COCO-Text — polygon/word-level annotations aggregated to page level | G4-1 (intermediate classes), G4-4 (pixel-ratio labels) |
| VLM labeling | Muharaf, PUCIT-OHUL, IAM (validation), COCO-Text blurred subset | G4-2 (6-class legibility), G4-5 (continuous legibility score) |
| Synthetic composition | New script required | G4-1 (SUBSTANTIAL class), G4-3 (MIXED_PRINTED_HW, MIXED_TYPED_HW) |

### Per-Source Dataset Analysis

**HierText** (8,281 train images)

Word-level polygon annotations include a `handwritten` boolean and `legible` boolean per word. Page-level labels are derived by aggregating these:

- `presence_score` (G4-4): pixel-area ratio from polygon geometry — the only gold-standard continuous label source in the pool. Implementation not yet created (HW-PRES-REG-G02).
- `presence_cls` (G4-1): presence class derived from area-ratio thresholds (MARGINAL < 10%, PARTIAL 10–50%). Intermediate class labeling not yet implemented (HW-PRES-D02).
- `legibility_cls` (G4-2): word-level ratio aggregated to page score; boundary images require VLM validation.
- Coverage: primarily 0.0–0.30 presence range; provides the only natural source of intermediate presence scores.

**COCO-Text** (43,686 train images; subset usable)

Word-level annotations include `class: machine_printed | handwritten` and `legibility: legible | illegible | others`. Usable but requires schema translation:

- G4-1: mostly NONE/MARGINAL (predominantly scene text; handwriting polygon coverage sparse — requires audit).
- G4-2: existing 3-class legibility schema (`clear / blurred / others`) not directly mappable to the 6-class target; VLM required for `blurred` and `others` subsets (~25K images).
- G4-4: bounding-box area proxy — overestimates handwriting coverage by ~5–15%; bias correction factor not yet quantified (HW-PRES-REG-D03).

**IAM Handwriting Database** (~13,000 pages, 657 writers)

Full handwriting corpus, all pages. Labels:

- G4-1: DOMINANT (all pages assign DOMINANT by corpus design).
- G4-4: fixed midpoint ~0.95 (tier_2_heuristic — no per-page variance; produces quantized not continuous labels).
- G4-2: EXCELLENT by heuristic (curated database; validate 10% via VLM).
- G4-5: fixed range ~0.90–1.00 (no within-corpus variance).
- G4-3: HANDWRITTEN_CURSIVE dominant, but cursive/block split per page not annotated; requires per-image VLM (IAA ~55–65%).

**Muharaf** (~22,000 pages; GCS-only locally, no local access)

Arabic handwriting corpus. All pages DOMINANT. Labels:

- G4-1: DOMINANT by corpus design.
- G4-2, G4-5: no legibility annotations; full VLM pass required (~20K images).
- G4-3: HANDWRITTEN_CURSIVE (Arabic script, all cursive by design).
- LOCAL LIMITATION: Muharaf is GCS-only; all operations require GCS VM access. Dry-run produced 0 records from this source.

**NIST SD-19** (~58,000 character-level samples; page-level status unclear)

Large character-level handwriting corpus requiring page reconstruction before use. Predominantly block-print style (form fill-ins, alphanumeric entries):

- G4-1: DOMINANT after page reconstruction.
- G4-3: HANDWRITTEN_BLOCK dominant.
- G4-4: fixed ~1.0 (corpus-level heuristic).
- Status: page reconstruction strategy and feasibility for this use case not yet validated.

**PUCIT-OHUL** (~7,000 pages; GCS-only locally, no local access)

Urdu/Nastaliq handwriting corpus. All pages DOMINANT. Labels:

- G4-1: DOMINANT by corpus design.
- G4-2, G4-5: no legibility annotations; full VLM pass required; Nastaliq calligraphic script VLM capability unvalidated.
- LOCAL LIMITATION: GCS-only; requires GCS VM access. Produces 0 records in local dry-runs.

**DocLayNet, TableBank, RVL-CDIP** (printed negatives)

- G4-1: NONE by `all_printed` strategy.
- G4-2: N_A (no handwriting present — deterministic, no annotation required).
- G4-3: N_A (DocLayNet/TableBank); PRINTED or TYPED (RVL-CDIP, requires VLM split).
- G4-4: presence_score = -1.0 (N_A sentinel, task_mask=0 — Defect 1 fix).
- G4-5: legibility_score = -1.0 (N_A sentinel, task_mask=0).
- These sources are trivially abundant; all require sampling caps.

### Critical Class and Score Gaps

**MARGINAL / PARTIAL / SUBSTANTIAL classes (G4-1)**: Zero labeled examples from any current source. These three classes define the most common real-world handwriting scenarios (signed forms, answer sheets, annotated documents). The label implementation (pixel-ratio conversion) does not exist. SUBSTANTIAL additionally requires a synthetic composition script that has not been built.

**ILLEGIBLE class (G4-2)**: Zero training examples. All curated handwriting corpora filter out unreadable images by design. This structural gap cannot be resolved by additional sampling from existing sources. Remediation requires sourcing real historical degraded manuscripts (~500 images minimum) or synthesizing proxy ILLEGIBLE examples via heavy augmentation (Gaussian blur sigma ≥ 5, elastic distortion) applied to FAIR-class images. Either path is not yet started.

**MIXED_PRINTED_HW and MIXED_TYPED_HW classes (G4-3)**: Near-zero natural examples. FUNSD provides ~149 pages of the MIXED_PRINTED_HW archetype — far below the 6,000-example target. MIXED_TYPED_HW has essentially zero sources in the current inventory. Both classes require a synthetic composition pipeline that has not been built.

**Score range 0.20–0.70 (G4-4)**: Fewer than 3,000 images from all sources combined provide mid-range presence scores. The pool is structurally bimodal: spike at 0.0 (printed negatives) and spike at ~0.95 (handwriting corpora). A regression head trained on this distribution learns a step function, not a continuous regressor.

**Score range 0.00–0.20 (G4-5)**: Zero training examples for the ILLEGIBLE/POOR legibility range. Structural curation bias eliminates low-legibility content from all curated handwriting corpora. The model cannot learn to predict low legibility scores with no training anchors in this region.

### Pool Summary

| Class / Range | Available (Pre-Cap) | After Cap | Status |
|---------------|---------------------|-----------|--------|
| G4-1 NONE | >350,000 | 12,000 | ✅ Available (cap required) |
| G4-1 MARGINAL | ~0 | 0 | ❌ Blocked — pixel-ratio not implemented |
| G4-1 PARTIAL | ~0 | 0 | ❌ Blocked — pixel-ratio not implemented |
| G4-1 SUBSTANTIAL | ~0 | 0 | ❌ Blocked — synthetic composition required |
| G4-1 DOMINANT | ~50,000 (after GCS) | 12,000 | ⚠️ Available after GCS access |
| G4-2 N_A | >350,000 | ~30,000 | ✅ Available |
| G4-2 ILLEGIBLE | 0 | 0 | ❌ Blocked — no natural source |
| G4-2 POOR | ~0 (trace) | ~1,500 target | ❌ Near-zero; requires VLM |
| G4-2 FAIR | ~0 (requires VLM) | ~4,500 target | ⚠️ Requires VLM labeling |
| G4-2 GOOD | ~0 (requires VLM) | ~9,000 target | ⚠️ Requires VLM labeling |
| G4-2 EXCELLENT | ~13,000 (IAM) | ~12,000 | ✅ Available after heuristic assignment |
| G4-3 MIXED_PRINTED_HW | ~149 (FUNSD) | 6,000 target | ❌ 2% of target; synthetic composition required |
| G4-3 MIXED_TYPED_HW | ~0 | 6,000 target | ❌ Near-zero; archive acquisition required |
| G4-4 score 0.20–0.70 | <3,000 | 15,000 target | ❌ Critical gap; bimodal distribution |
| G4-5 score 0.00–0.20 | 0 | ~1,200 target | ❌ Blocked — curation bias |

---

## Section 4 — Label Schema

### N_A Sentinel Defect (CRITICAL — Fix Before Any Assembly)

`legibility_score` (G4-5) and `presence_score` (G4-4) must use **-1.0** as the sentinel for images with no handwriting (presence = NONE), not 0.0. The masked loss mechanism sets the loss weight to 0 for all N_A images. If 0.0 is used as the sentinel, the model trains on spurious targets and learns to output near-zero scores for every printed page, conflating "no handwriting" with "completely illegible handwriting." This defect appears in the scaffold documentation and must be corrected in all assembly scripts, manifest schemas, and training code before any manifests are generated (HW-LEG-REG-G02).

### G4-1: `handwriting_assessment.presence`

| Field | Value |
|-------|-------|
| **Type** | 5-class enum (UPPER_SNAKE_CASE) |
| **Classes** | NONE (0% area), MARGINAL (< 10%), PARTIAL (10–50%), SUBSTANTIAL (50–90%), DOMINANT (> 90%) |
| **Derivation** | `all_handwritten` → DOMINANT; `all_printed` → NONE; `model_derived` → pixel-ratio area computation from polygon annotations |
| **Provenance** | tier_0_exact for NONE/DOMINANT (heuristic by corpus); tier_1_annotation for MARGINAL/PARTIAL (polygon pixel-ratio); tier_2_heuristic for SUBSTANTIAL (synthetic composition) |
| **Boundary Risk** | MARGINAL/PARTIAL boundary (10%) and PARTIAL/SUBSTANTIAL boundary (50%) — VLM Tier 2 validation required on 20% of boundary-zone images; ±2% dead-zone recommended around both thresholds |

### G4-2: `handwriting_assessment.legibility`

| Field | Value |
|-------|-------|
| **Type** | 6-class enum (UPPER_SNAKE_CASE for most; N_A uses underscore) |
| **Classes** | N_A (presence = NONE), ILLEGIBLE (unrecoverable), POOR (very difficult), FAIR (readable with effort), GOOD (minimal effort), EXCELLENT (near-print quality) |
| **Derivation** | N_A: deterministic from presence=NONE; EXCELLENT: heuristic from IAM; GOOD/FAIR: VLM on COCO-Text and HierText; POOR: VLM on COCO-Text blurred tail and PUCIT-OHUL; ILLEGIBLE: not yet sourceable |
| **Provenance** | tier_1_annotation (VLM); tier_2_heuristic (IAM EXCELLENT); N_A is deterministic |
| **IAA Note** | IAA for legibility judgments is 60–70%. The Macro F1 ≥ 0.72 original target exceeds the theoretical achievable ceiling. Revised target: Macro F1 ≥ 0.60. |
| **Loss Function** | Standard softmax cross-entropy + label smoothing (epsilon = 0.10); N_A is categorical, not ordinal — pure ordinal regression (CORAL) is inappropriate without masking N_A separately |

### G4-3: `handwriting_assessment.content_type`

| Field | Value |
|-------|-------|
| **Type** | 7-class enum (UPPER_SNAKE_CASE) |
| **Classes** | N_A (presence = NONE), PRINTED (digital/offset print), TYPED (typewriter), HANDWRITTEN_CURSIVE (joined letterforms), HANDWRITTEN_BLOCK (disconnected letterforms), MIXED_PRINTED_HW (printed base + handwritten annotations), MIXED_TYPED_HW (typewriter text + handwritten annotations) |
| **Derivation** | N_A / PRINTED: rule-based; TYPED: VLM on RVL-CDIP letter/memo subset; HANDWRITTEN_CURSIVE: corpus-level (Muharaf/PUCIT-OHUL/KHATT) + per-image VLM for IAM; HANDWRITTEN_BLOCK: per-image VLM on IAM and NIST-SD2; MIXED classes: synthetic composition (primary path) + VLM on FUNSD and RVL-CDIP form subset |
| **Dependency** | Serial dependency on G4-1 — all handwriting-present content_type labels require presence labels to be resolved first |
| **IAA Risk** | HANDWRITTEN_CURSIVE vs. HANDWRITTEN_BLOCK: IAA ~55–65% — below the 70% minimum. Governance decision required: measure IAA on 200 IAM pages before committing to the full 7-class schema; if kappa < 0.50, collapse to single HANDWRITTEN class |

### G4-4: `handwriting_assessment.presence_score`

| Field | Value |
|-------|-------|
| **Type** | float [0.0, 1.0] |
| **Semantics** | Area fraction of page covered by handwriting pixels; 0.0 = no handwriting, 1.0 = entirely handwritten |
| **Derivation** | tier_0_exact: pixel-area ratio from HierText polygon annotations (gold standard, 8,281 images); tier_1_annotation: bounding-box proxy from COCO-Text (with bias correction); tier_2_heuristic: corpus-level midpoints (IAM→0.95, DocLayNet→0.0) |
| **N_A Sentinel** | -1.0 (masked loss) — NOT 0.0. See sentinel defect note above. |
| **Output Head** | Gaussian NLL (mu, sigma_sq); sigma_sq assigned by confidence tier: tier_0→0.01, tier_1→0.05, tier_2→0.15 |
| **Alignment with G4-1** | presence_cls boundaries: NONE 0.0–0.01, MARGINAL 0.01–0.10, PARTIAL 0.10–0.50, SUBSTANTIAL 0.50–0.90, DOMINANT 0.90–1.00 — same image must have logically consistent presence_score and presence class |
| **Bimodal Warning** | Corpus-level midpoint mapping produces quantized targets clustered at discrete anchors (0.0 and ~0.95), not a continuous distribution. This causes the Gaussian NLL head to drive sigma_sq→0 at anchor points, defeating uncertainty modeling. The Pearson r ≥ 0.80 target is spuriously achievable on a bimodal test set without meaningful mid-range regression capability. |

### G4-5: `handwriting_assessment.legibility_score`

| Field | Value |
|-------|-------|
| **Type** | float [0.0, 1.0] |
| **Semantics** | 0.0 = completely illegible, 1.0 = perfect legibility equivalent to printed text |
| **Derivation** | No dataset has direct human MOS ratings. VLM labeling (5-point scale, normalized to 0–1) is the only tractable path. Requires calibration study against human ratings on ≥ 300 images before large-scale deployment. |
| **N_A Sentinel** | -1.0 (masked loss) — NOT 0.0. See sentinel defect note above. |
| **Class-to-Score Mapping** | Provisional anchors (require empirical MOS calibration before use): ILLEGIBLE 0.05–0.15, POOR 0.20–0.35, FAIR 0.40–0.55, GOOD 0.60–0.80, EXCELLENT 0.90–1.00. Linear interpolation is not empirically supported — inter-class perceptual distances are non-uniform. |
| **Output Head** | Gaussian NLL (mu, sigma_sq); sigma_sq is semantically meaningful only with human MOS variance as ground truth — without MOS data, sigma_sq models VLM label noise, not genuine legibility ambiguity |
| **IAA Ceiling** | IAA 60–70% implies Pearson r ceiling ~0.60–0.65 against human ratings. Revised target: Pearson r ≥ 0.55 vs human MOS. |
| **VLM Circular Validation Risk** | If VLM assigns training labels AND evaluates OOD images, Pearson r measures VLM self-consistency, not model accuracy. Human-rated OOD evaluation (≥ 100 images, ≥ 3 raters) is required for meaningful evaluation. |

### Training Manifest Record Schema

```json
{
  "image_path": "handwriting/images/{filename}.jpg",
  "source_dataset": "{hiertext|coco_text|iam|muharaf|nist_sd19|pucit_ohul|doclaynet|...}",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_1_annotation",
  "label_confidence": 0.8,
  "handwriting_presence": "PARTIAL",
  "handwriting_legibility": "GOOD",
  "handwriting_content_type": "MIXED_PRINTED_HW",
  "handwriting_presence_score": 0.32,
  "handwriting_legibility_score": 0.68,
  "na_mask_presence_score": false,
  "na_mask_legibility_score": false,
  "capture_method": "scanner"
}
```

For printed negatives (presence = NONE): `handwriting_presence = "NONE"`, `handwriting_legibility = "N_A"`, `handwriting_content_type = "N_A"`, `presence_score = -1.0` (N_A sentinel — Defect 1 fix; was incorrectly 0.0), `legibility_score = -1.0`, `na_mask_presence_score = true`, `na_mask_legibility_score = true`.

---

## Section 5 — Composition and Splits

All five G4 heads share the same 60,000-image training set. Each image carries labels for all five heads simultaneously. The class distributions below describe the target state after P0 gaps are resolved; the current state is 0 valid multi-label images assembled.

### G4-1: presence_cls Target Distribution

| Class | Area Threshold | Target Count | Target % | Primary Source |
|-------|---------------|-------------|----------|----------------|
| NONE | 0% | 12,000 | 20% | DocLayNet, TableBank, RVL-CDIP (capped) |
| MARGINAL | < 10% | 12,000 | 20% | HierText pixel-ratio (not yet implemented) |
| PARTIAL | 10–50% | 12,000 | 20% | HierText pixel-ratio + synthetic fallback |
| SUBSTANTIAL | 50–90% | 12,000 | 20% | Synthetic composition (script not yet built) |
| DOMINANT | > 90% | 12,000 | 20% | IAM + NIST-SD2 + Muharaf + PUCIT-OHUL (capped from ~50K) |

### G4-2: legibility_cls Target Distribution

| Class | Target Count | Primary Source | Risk |
|-------|-------------|----------------|------|
| N_A | ~30,000 (50% of set) | Printed negatives (deterministic) | LOW |
| ILLEGIBLE | ≥ 500 (absolute minimum) | Historical archives or heavy augmentation of FAIR images | CRITICAL — 0 examples |
| POOR | ≥ 1,500 (5% of HW images) | COCO-Text blurred tail, PUCIT-OHUL VLM-labeled | HIGH |
| FAIR | ≥ 4,500 (15% of HW images) | COCO-Text blurred, Muharaf/PUCIT-OHUL VLM-labeled | HIGH |
| GOOD | ≥ 9,000 (30% of HW images) | COCO-Text clear, HierText VLM-labeled | MEDIUM |
| EXCELLENT | ≥ 12,000 (40% of HW images) | IAM (heuristic), COCO-Text clear, Muharaf VLM-labeled | LOW |

### G4-3: content_type_cls Target Distribution

| Class | Target Count | Target % | Primary Source | Risk |
|-------|-------------|----------|----------------|------|
| N_A | 12,000 | 20% | Printed negatives | LOW |
| PRINTED | 12,000 | 20% | Born-digital sources (rule-based) | LOW |
| TYPED | 6,000 | 10% | RVL-CDIP letter/memo subset (VLM) | MEDIUM |
| HANDWRITTEN_CURSIVE | 12,000 | 20% | IAM + Muharaf + PUCIT-OHUL + KHATT | LOW after GCS |
| HANDWRITTEN_BLOCK | 6,000 | 10% | NIST-SD2 + IAM block fraction (VLM split) | MEDIUM |
| MIXED_PRINTED_HW | 6,000 | 10% | Synthetic composition (primary) + FUNSD | CRITICAL — ~2% of target naturally available |
| MIXED_TYPED_HW | 6,000 | 10% | Synthetic composition + archive acquisition | CRITICAL — near-zero available |

### G4-4: presence_reg Score Distribution

| Score Range | Class Correspondence | Target % | Target Count | Source Quality |
|-------------|---------------------|----------|-------------|----------------|
| 0.00 (exact) | NONE | ~15–20% | ~9,000–12,000 | tier_2_heuristic (corpus-level) |
| 0.01–0.19 | MARGINAL | ≥ 15% | 9,000 | tier_0 to tier_1 (HierText polygon + COCO-Text proxy) |
| 0.20–0.69 | PARTIAL / SUBSTANTIAL | ≥ 25% | 15,000 | CRITICAL GAP — <3,000 available from any source |
| 0.70–0.89 | SUBSTANTIAL | ≥ 10% | 6,000 | tier_2_heuristic (VLM-estimated outliers) |
| 0.90–1.00 | DOMINANT | ~20–25% | 12,000–15,000 | tier_2_heuristic (corpus-level midpoints) |

### G4-5: legibility_reg Score Distribution

| Score Range | Class Correspondence | Target % | Target Count | Risk |
|-------------|---------------------|----------|-------------|------|
| 0.00–0.20 | ILLEGIBLE | ≥ 2% | ~1,200 | CRITICAL — 0 examples; structural gap |
| 0.20–0.35 | POOR | ≥ 5% | ~3,000 | HIGH — requires VLM; count uncertain |
| 0.35–0.55 | FAIR | ≥ 15% | ~9,000 | HIGH — requires VLM |
| 0.55–0.80 | GOOD | ≥ 30% | ~18,000 | MEDIUM — VLM quality likely adequate |
| 0.80–1.00 | EXCELLENT | ≥ 40% | ~24,000 | LOW — structurally well covered |
| N_A (masked) | No handwriting | ~50% | ~30,000 | ✅ Deterministic from presence labels |

### Split Strategy

| Split | Images | Percentage |
|-------|-------:|------------|
| Train | 42,000 | 70% |
| Val | 9,000 | 15% |
| Test | 9,000 | 15% |
| **Total** | **60,000** | **100%** |

**Split Method**: Stratified by source dataset and presence class simultaneously; image-level SHA256 keyed via global split registry.

**Leakage Prevention**: All five G4 heads share the same 60,000-image set. An image assigned to the presence_cls val split must appear in the val split for all other G4 heads — enforced by the global split registry before any manifests are generated. HierText test split must be registered as held-out for G4-4 Pearson r evaluation before assembly begins. SHA256 + pHash dedup (Hamming ≤ 5) required against OOD-Handwriting images before assembly.

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audit**: [handwriting_ddr.md](../diversity_reports/handwriting_ddr.md)
> **Overall Diversity Score**: 20/100 (DDR automated score; 0 samples loaded — dataset not assembled)

G4-1 estimated diversity (pre-assembly projection): 22/100. G4-2, G4-4, G4-5: 0/100 (datasets not assembled). G4-3: 18/100 (pre-assembly projection). All scores are structural assessments based on source pool analysis; actual scores require assembled dataset.

| Dimension | L2 Field | Relevance | Target | Current Estimate | Status |
|-----------|----------|-----------|--------|-----------------|--------|
| class_balance | `handwriting_assessment.presence` | CRITICAL | ~12,000 per presence class | NONE: abundant; DOMINANT: ~50K avail; MARGINAL/PARTIAL/SUBSTANTIAL: 0 | ❌ 3 of 5 classes absent |
| script_diversity | `language.script_code` | CRITICAL | ≥ 5 scripts (LATN, ARAB, URDU, HANS, DEVA) | LATN (IAM, HierText, COCO-Text), ARAB (Muharaf), URDU (PUCIT-OHUL) — CJK/Deva/Cyrillic absent | ❌ 3 of 5 target scripts absent |
| mixed_content | `handwriting_assessment.is_mixed` | CRITICAL | ≥ 30% mixed pages | Near zero — MARGINAL/PARTIAL/SUBSTANTIAL classes all absent | ❌ |
| score_distribution | `handwriting_assessment.presence_score` | CRITICAL (G4-4/G4-5) | Reasonably uniform 0–1 density | Bimodal: spike at 0.0 and ~0.95; 0.20–0.70 near-empty | ❌ |
| document_age | `image_properties.document_age` | HIGH | All 3 ages (modern, aged, historical) | Mostly modern; historical virtually absent; historical is primary ILLEGIBLE/POOR source | ❌ |
| capture_method | `capture_method.method` | HIGH | ≥ 3 methods (born_digital, scanner, camera) | born_digital (negatives), scanner (IAM/NIST-SD2), camera (HierText/COCO-Text scene) | ⚠️ Camera examples are scene text, not dedicated handwriting pages |
| handwriting_style | `handwriting_assessment.content_type` | HIGH | All 7 content types | HANDWRITTEN_CURSIVE (IAM/Muharaf); HANDWRITTEN_BLOCK (NIST-SD2/IAM partial); MIXED classes absent | ❌ MIXED classes structurally absent |
| degradation | `quality.degradations` | HIGH (G4-2/G4-5) | ≥ 3 types (blur, aging, bleed-through) | IAM/NIST-SD2 are clean scans; degraded HW examples absent | ❌ |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | Grayscale dominant (IAM, NIST-SD2); some color in scene text datasets | ⚠️ |
| domain | `domain.level1` | MEDIUM | ≥ 5 domains | Academic (IAM), financial (NIST-SD2), natural scene (HierText) | ⚠️ Medical/legal absent |
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers | Scanner-sourced ~300 DPI; limited variation | ⚠️ |
| layout_type | `structure.layout_type` | MEDIUM | ≥ 3 types (pure manuscript, form, mixed) | Pure manuscript (DOMINANT class); born-digital (NONE class); mixed layouts absent | ❌ |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | Letters/notes (IAM), forms (NIST-SD2), scene images (HierText) | ⚠️ |
| background_complexity | `image_properties.background` | LOW | Plain and complex | Plain dominant (IAM); complex in scene text only | ⚠️ |

### Key Diversity Gaps

- **Script coverage is critically limited to Latin/Arabic/Urdu.** SigLIP 2 visual features will be biased toward Latin-family handwriting. CJK, Devanagari, and Cyrillic handwriting appear in production and in the OOD set but have zero training signal. This creates a systematic Latin-family bias across all five G4 heads.
- **Mixed content pages are the defining characteristic of three presence classes (MARGINAL, PARTIAL, SUBSTANTIAL) and two content_type classes (MIXED_PRINTED_HW, MIXED_TYPED_HW).** The absence of these classes is not merely a diversity gap — it is a direct statement that five of the twelve non-trivial label classes have zero training examples.
- **Historical documents are the natural source for ILLEGIBLE and POOR legibility examples.** Zero historical handwriting datasets are in the training pool, simultaneously blocking the legibility low-end and the `document_age=historical` diversity dimension.
- **CJK handwriting absent entirely:** No training source. CASIA-HWDB is OOD-only (sub-source 5b). At inference, the model will encounter CJK handwriting (common in Unify's production document set) with no training signal.

---

## Section 7 — Wild Condition Coverage

> **Overall Wild Condition Score**: 18/100 for G4-1 (pre-assembly projection); 0/100 for G4-2, G4-4, G4-5 (not assembled); 12/100 for G4-3 (pre-assembly projection)

The most critical wild conditions for this dataset are the class archetype scenarios: each of the three absent presence classes (MARGINAL, PARTIAL, SUBSTANTIAL) and each of the two absent content_type classes (MIXED_PRINTED_HW, MIXED_TYPED_HW) represents a wild condition by definition — they are conditions the model must classify but has never been trained on.

| Wild Condition | L2 Evidence | Status | Gap |
|----------------|-------------|--------|-----|
| Typed form with single handwritten signature — MARGINAL archetype (< 10% handwriting area) | `handwriting_assessment.presence` = MARGINAL | ❌ Missing | Defines the MARGINAL class; pixel-ratio labeling not implemented; no dedicated source at scale |
| School exercise: printed instructions + handwritten answers — PARTIAL archetype (10–50% area) | `handwriting_assessment.presence` = PARTIAL | ❌ Missing | HierText may yield partial coverage after pixel-ratio implementation; count unquantified |
| Research notebook: printed headings + extensive handwritten notes — SUBSTANTIAL archetype (50–90% area) | `handwriting_assessment.presence` = SUBSTANTIAL | ❌ Missing | No natural source identified; synthetic composition required; not yet built |
| ILLEGIBLE handwriting (truly unrecoverable by human expert) | `handwriting_assessment.legibility` = ILLEGIBLE | ❌ Missing | Zero training examples; OOD-only via KHATT 5a (20+ pages); model will conflate ILLEGIBLE with POOR or N_A at inference |
| Printed document with handwritten margin annotations — MIXED_PRINTED_HW archetype | `handwriting_assessment.content_type` = MIXED_PRINTED_HW | ❌ Missing | FUNSD provides ~149 examples; target is 6,000; synthetic composition required |
| Typewriter document with handwritten annotations — MIXED_TYPED_HW archetype | `handwriting_assessment.content_type` = MIXED_TYPED_HW | ❌ Missing | Near-zero natural source; archive acquisition required; the rarest mixed-content class |
| CJK handwriting (CASIA-HWDB style) | `language.script_code` = Hans/Hant | ❌ Missing (OOD only) | Absent from all training sources; tested in OOD-Handwriting 5b; model will be untrained on CJK handwriting in production |
| Devanagari handwriting | `language.script_code` = Deva | ❌ Missing (OOD only) | Absent from all training sources; tested in OOD-Handwriting 5c |
| Faded or aged handwriting approaching illegibility | `image_properties.document_age`, `quality.degradations` (ink_fading) | ❌ Missing | Clean scanner captures dominate DOMINANT class; IAM/NIST-SD2 are well-preserved scans; primary real-world source of POOR/ILLEGIBLE scores |
| Camera-captured handwritten notes with glare and perspective distortion | `capture_method.method` = camera_smartphone | ⚠️ Partial | HierText has camera-captured scene text; IAM is flatbed-scanned; dedicated camera-captured handwriting pages absent |
| Non-Latin cursive scripts: Arabic handwriting mixed with printed text | `language.script_code` = Arab, `handwriting_assessment.is_mixed` | ⚠️ Partial | Muharaf covers pure Arabic HW (DOMINANT only); mixed Arabic HW + printed text absent |
| Medical / prescription writing (notoriously illegible small tight cursive) | `handwriting_assessment.legibility` = ILLEGIBLE/POOR | ❌ Missing | No medical handwriting dataset in training pool; primary real-world source of ILLEGIBLE scores |
| Pencil handwriting (low contrast, prone to smearing) | `quality.degradations` | ❌ Missing | Absent from all curated HW datasets; primary mechanical cause of POOR legibility scores |

**Wild condition tally**: 2 partial, 11 missing, 0 fully covered. The most critical gap is that the five "archetype" wild conditions (MARGINAL, PARTIAL, SUBSTANTIAL, MIXED_PRINTED_HW, MIXED_TYPED_HW) are absent from training — each of these defines a label class the model must predict but has no training signal for.

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
> **HAR Section 6 Reference**: All five G4 HAR files, Section 6

All five G4 heads share the same OOD-Handwriting category (Phase 5, P0, 500 total images).

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Handwriting |
| **OOD Target Images** | 500 |
| **OOD Acquisition Status** | Not started (Phase 5, P0) |

| OOD Sub-source | Images | Relevance | Stress Scenario |
|----------------|-------:|-----------|-----------------|
| 5a. KHATT Arabic cursive | 200 | ✅ Direct | RTL handwriting (Arabic) not in training; includes ≥ 20 ILLEGIBLE pages — the only identified evaluation source for the ILLEGIBLE class absent from training. Must be expanded to ≥ 50 ILLEGIBLE examples for reliable per-class F1 estimation (standard error on F1 with 20 examples > 0.07). |
| 5b. CASIA-HWDB CJK handwritten | 150 | ✅ Direct | CJK character handwriting entirely absent from training; tests whether HANDWRITTEN_CURSIVE generalizes beyond alphabetic scripts. 2–4 week access lead time for CASIA-HWDB; SCUT-HCCDoc is the open fallback. |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | ✅ Direct | Devanagari absent from training; tests Indian subcontinent handwriting generalization; legibility criteria differ from Latin. |
| 5d. Specialized content handwriting | 50 | ⚠️ Indirect | Mathematical notation and engineering drawings; content_type closest class is HANDWRITTEN_CURSIVE or HANDWRITTEN_BLOCK (note: `specialized` from older scaffold schema is not a class in the current 7-class schema); legibility scoring by expert rating preferred over VLM for this sub-source. |

### OOD Design Gaps

The current OOD design adequately covers non-Latin script stress (three of four sub-sources), but has two structural gaps:

1. **MIXED class failure modes untested.** No OOD sub-source covers MIXED_PRINTED_HW or MIXED_TYPED_HW scenarios. These are the most critical production failure modes — real business documents frequently present as mixed typed/printed with handwritten annotations. Proposed additions: sub-source 5e (50 real MIXED_PRINTED_HW examples from library archives), sub-source 5f (50 TYPED documents with degradation for content_type_cls TYPED class generalization).

2. **Mid-range presence_reg and legibility_reg untested.** Sub-sources 5a–5c are predominantly DOMINANT presence (0.70–1.0) and EXCELLENT/GOOD legibility. Sub-source 5d (50 images) is the only potential mid-range score source — far too small for statistically meaningful Pearson r estimation in the 0.10–0.60 range. Proposed addition: 50–100 annotated form fill-in examples (FUNSD-style) with pixel-level presence scores.

3. **Human OOD ratings absent.** If VLM provides both training legibility labels (G4-5) and OOD evaluation scores, Pearson r measures VLM self-consistency not model accuracy. Human-rated legibility scores (≥ 3 raters) are required on at least 100 OOD images before meaningful G4-5 evaluation is possible.

**OOD Leakage Risk**: MEDIUM. KHATT, CASIA-HWDB, and IIIT-INDIC are not in the training pool (LOW direct overlap). Main risk: COCO-Text images used as PRINTED/N_A training examples may share document origins with scene text images appearing in OOD sub-sources. SHA256 + pHash dedup (Hamming ≤ 5) required against all training sources before OOD registration. The ILLEGIBLE class in KHATT 5a intentionally tests a class absent from training — this is expected evaluation behavior, not a leakage scenario.

---

## Section 9 — Assembly Pipeline

**Status**: ❌ Blocked — `handwriting` subcommand not implemented; labeling infrastructure absent; N_A sentinel defect must be fixed first

### Assembly Commands (Once Unblocked)

```bash
# Prerequisites (run in strict order)

# Step 0: Fix N_A sentinel defect (governance action)
# Correct all assembly scripts and manifest schemas:
# legibility_score N_A sentinel = -1.0 (NOT 0.0)
# presence_score N_A sentinel = -1.0 (NOT 0.0, only for masked images)

# Step 1: Implement HierText pixel-ratio area computation
# (creates presence_score gold-standard labels and presence_cls intermediate classes)
# Script: TBD (HW-PRES-G02, HW-PRES-REG-G02)

# Step 2: Implement 5-class label conversion in harmonize_handwriting_labels.py
# (maps all_handwritten -> DOMINANT, all_printed -> NONE, model_derived -> pixel-ratio)
# Script: scripts/harmonize_handwriting_labels.py (HW-PRES-G01)

# Step 3: Implement synthetic composition for SUBSTANTIAL class and MIXED classes
# (overlay handwriting crops onto printed document backgrounds at target area coverage)
# Script: TBD (HW-PRES-G04, HW-CONT-G02, HW-CONT-G03)

# Step 4: Run VLM legibility labeling on COCO-Text blurred/others subsets (~25K images)
# (HW-LEG-G02, HW-LEG-G04)

# Step 5: Run VLM legibility + content_type labeling on Muharaf and PUCIT-OHUL (GCS VM)
# (HW-LEG-G05, HW-CONT-G08)

# Step 6: Implement handwriting subcommand in prepare_multitask_datasets.py
# (HW-PRES-G05, shared across all G4 heads)

# Step 7: Dry run (validates without writing)
uv run python scripts/prepare_multitask_datasets.py handwriting --dry-run

# Step 8: Full assembly run (GCS VM recommended for Muharaf/PUCIT-OHUL access)
uv run python scripts/prepare_multitask_datasets.py handwriting
```

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| N_A sentinel fix (-1.0 not 0.0) | ❌ Not done | All G4 labels — prerequisite to everything |
| HierText pixel-ratio script | ❌ Not created | G4-1 intermediate classes, G4-4 gold-standard labels |
| 5-class presence label conversion in `harmonize_handwriting_labels.py` | ❌ Not implemented | G4-1 label generation |
| Synthetic composition script (SUBSTANTIAL + MIXED classes) | ❌ Not created | G4-1 SUBSTANTIAL class, G4-3 MIXED_PRINTED_HW / MIXED_TYPED_HW |
| VLM legibility labeling pipeline (COCO-Text blurred, Muharaf, PUCIT-OHUL) | ❌ Not run | G4-2 FAIR/POOR/ILLEGIBLE classes, G4-5 labeling |
| `handwriting` subcommand in `prepare_multitask_datasets.py` | ❌ Not implemented | All G4 heads — assembly pipeline |
| `harmonize_handwriting_labels.py` (binary version exists) | ⚠️ Partial | Dry-run complete (38,967 binary records); 5-class conversion required |
| Muharaf data (GCS-only locally) | ⚠️ GCS-only | ~22K DOMINANT images; requires GCS VM access for full run |
| PUCIT-OHUL data (GCS-only locally) | ⚠️ GCS-only | ~7K DOMINANT images; requires GCS VM access |
| Global split registry (SHA256-keyed) | ❌ Not deployed | Cross-head split consistency; HierText test split reservation |
| ILLEGIBLE training examples (500–1,000) | ❌ Not acquired | G4-2 ILLEGIBLE class, G4-5 low-end regression range |

### Dry-Run Results (2026-02-21, Binary Labels Only)

`scripts/harmonize_handwriting_labels.py` (binary presence detection, not 5-class) was run as a dry-run. Results:

- Total records: 38,967 — **this is a dry-run estimate only; actual assembled dataset = 0 images**
- Positive (has_handwriting = 1): 9,289 (24% of target 40K positive; short due to GCS-only Muharaf/PUCIT-OHUL)
- Label format: binary flag only — NOT 5-class enum; does not feed any G4 head in current form
- GCS-only datasets (Muharaf, PUCIT-OHUL): 0 records loaded locally
- These figures confirm the infrastructure exists but produces the wrong label type

### Generated Outputs (Target State)

| File | Description |
|------|-------------|
| `handwriting/train_manifest.json` | Flat JSON list of 42,000 training records with all 5 G4 labels |
| `handwriting/val_manifest.json` | Flat JSON list of 9,000 validation records |
| `handwriting/test_manifest.json` | Flat JSON list of 9,000 test records (HierText portion held for G4-4 Pearson r) |
| `handwriting/images/` | Local image copies (or GCS path `gs://image_detection_b/handwriting_training/images/`) |

---

## Section 10 — Gap Registry

All gap IDs are verbatim from the five G4 HAR files. Gaps are grouped by root cause to clarify the resolution order; the N_A sentinel defect is prerequisite to all others.

### Root Cause Groups

**Group A — N_A Sentinel Defect (prerequisite to all G4 assembly)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-LEG-REG-G02 | `legibility_score` N_A sentinel uses 0.0 in scaffold; masked loss requires -1.0; propagates to all assembly scripts and manifest schemas | G4-5 (and G4-4 by extension) | Correct sentinel to -1.0 in all assembly scripts, manifest schemas, and documentation before any training manifests are generated | 0.5 days |

**Group B — Label Infrastructure (P0 — no labels exist for any head)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-PRES-G01 | `harmonize_handwriting_labels.py` outputs binary flag only; 5-class presence enum not implemented | G4-1 | Extend script: add `all_handwritten`→DOMINANT, `all_printed`→NONE, and pixel-ratio logic for `model_derived` sources | 2 days |
| HW-PRES-G05 | `handwriting` subcommand of `prepare_multitask_datasets.py` not implemented | All G4 | Implement following established script/orientation/shadow pattern; include NONE/DOMINANT sampling caps (12K each) | 2 days |
| HW-LEG-G03 | Same handwriting subcommand blocker (shared with G4-1) | G4-2 | See HW-PRES-G05 | Shared |
| HW-CONT-G05 | Same handwriting subcommand blocker (shared) | G4-3 | See HW-PRES-G05 | Shared |
| HW-PRES-REG-G04 | Same handwriting subcommand blocker (shared) | G4-4 | See HW-PRES-G05 | Shared |
| HW-LEG-REG-G06 | Same handwriting subcommand blocker (shared); must include masked loss flag and -1.0 sentinel for N_A images | G4-5 | See HW-PRES-G05 | Shared |

**Group C — Intermediate Presence Class Coverage (P0)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-PRES-G02 | MARGINAL class: 0 examples — pixel-ratio computation on HierText/COCO-Text polygon annotations not implemented | G4-1, G4-4 | Implement pixel-ratio area computation; filter HierText pages where 1–10% of area is handwritten | 2 days |
| HW-PRES-G03 | PARTIAL class: 0 examples — same pixel-ratio gap; HierText yield in 10–50% range uncertain | G4-1, G4-4 | Implement pixel-ratio; audit HierText PARTIAL yield; if insufficient, implement synthetic composition fallback | 2–4 days |
| HW-PRES-G04 | SUBSTANTIAL class: 0 examples — no natural source for 50–90% handwriting coverage | G4-1, G4-4 | Implement synthetic composition: overlay handwriting page crops onto printed document backgrounds at 50–90% area coverage | 3 days |
| HW-PRES-REG-G02 | HierText pixel-level area ratio computation script not yet created | G4-4 | Write script to compute handwriting pixel area ratio from HierText polygon annotations; validate against 50-image manual spot-check | 1 day |
| HW-PRES-REG-G03 | Score range 0.20–0.70 severely underrepresented — bimodal distribution; <3,000 mid-range examples | G4-4 | Audit HierText mid-range yield; if insufficient, implement synthetic mixed-document composition at varying coverage percentages | 2–4 days analysis + TBD composition |

**Group D — ILLEGIBLE Class Coverage (P0 — structural curation bias)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-LEG-G01 | ILLEGIBLE class: 0 training examples — all curated HW corpora filter unreadable images by design | G4-2 | Option A: Acquire ~500 real ILLEGIBLE examples from historical archives or medical datasets; Option B: Synthesize via heavy augmentation (Gaussian blur sigma ≥ 5, elastic distortion) on FAIR samples. Option B unblocks training schedule faster; real acquisition recommended in parallel for next cycle. | 2 days (Option A) or 0.5 days (Option B synthesis) |
| HW-LEG-REG-G04 | ILLEGIBLE range (0.00–0.20): 0 training anchors — regression head cannot learn this region | G4-5 | Source or synthesize 500–1,000 images with legibility_score ≤ 0.20; shared remediation path with HW-LEG-G01 | Shared with HW-LEG-G01 |

**Group E — MIXED Content Class Coverage (P0 — structural)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-CONT-G02 | MIXED_PRINTED_HW: ~149 natural examples vs. 6,000 target | G4-3 | Implement synthetic composition script overlaying handwriting annotation regions onto printed document pages at 10–30% area coverage; also audit RVL-CDIP form subset via VLM (estimated 2K–8K candidates) | 3–5 days |
| HW-CONT-G03 | MIXED_TYPED_HW: near-zero examples — more severe than MIXED_PRINTED_HW | G4-3 | Archive acquisition from historical typed document collections + synthetic composition on TYPED class examples; if yield < 500 after 2 weeks, propose schema revision (collapse to single MIXED class) | 3–5 days minimum; timeline uncertain |

**Group F — VLM Labeling Infrastructure (P0)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-LEG-G04 | `handwriting_assessment.legibility` L2 field unpopulated for all datasets | G4-2 | Implement VLM labeling pipeline (COCO-Text blurred/others ~25K; Muharaf ~20K; PUCIT-OHUL ~8K) | 3–5 days total VLM compute |
| HW-CONT-G01 | `handwriting_assessment.content_type` L2 field unpopulated for all datasets | G4-3 | Implement per-dataset labeling rules: rule-based for N_A/PRINTED; VLM for TYPED, HANDWRITTEN_BLOCK, MIXED classes | 2 days |
| HW-PRES-REG-G01 | `handwriting_assessment.presence_score` L2 field unpopulated for all datasets | G4-4 | Run pixel-ratio computation on HierText; run VLM estimation on Muharaf/PUCIT-OHUL; derive heuristic labels for remaining sources | 2–3 days |
| HW-LEG-REG-G01 | `handwriting_assessment.legibility_score` L2 field unpopulated for all datasets; VLM calibration against human MOS required | G4-5 | Run human MOS calibration study (≥ 300 images, ≥ 3 raters, spanning ILLEGIBLE through EXCELLENT) before large-scale VLM deployment | 1 day protocol + 3 days annotation for calibration set |

**Group G — CURSIVE/BLOCK Split (P0 governance)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-CONT-G04 | HANDWRITTEN_CURSIVE vs. HANDWRITTEN_BLOCK per-image split not implemented — IAM page-level style unknown; IAA ~55–65% on this distinction | G4-3 | Measure IAA on 200 IAM pages first; if kappa < 0.50, collapse to single HANDWRITTEN class and revise head spec; otherwise run VLM on full IAM (~13K) | 1 day IAA measurement + governance decision; then 1–2 days VLM if proceeding |

**Group H — Serial Dependency (P0)**

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-CONT-G06 | G4-3 (content_type_cls) serially blocked by G4-1 (presence_cls) P0 resolution — all handwriting-present content_type labels require presence labels first | G4-3 | Resolve G4-1 P0 gaps (HW-PRES-G01 through G05) in parallel; estimated 11–13 days | 11–13 days (in G4-1 scope) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Head(s) | Remediation | Effort |
|--------|-------------|---------|-------------|--------|
| HW-PRES-G06 | CJK handwriting absent — SigLIP visual features biased toward Latin-family | G4-1 through G4-5 | Source CASIA-HWDB or SCUT-HCCDoc; generate 5,000–10,000 CJK DOMINANT examples | 3–5 days (incl. access request) |
| HW-PRES-G07 | Devanagari handwriting absent | G4-1 through G4-5 | Source IIIT-HW or similar; 1,000–3,000 images minimum | 2–3 days |
| HW-PRES-G08 | Cyrillic handwriting absent | G4-1 through G4-5 | Source HKR dataset (Russian cursive); sample ~2,000 page-level images | 2 days |
| HW-PRES-G09 | MARGINAL/PARTIAL boundary precision low near 10% threshold — ±3–5% measurement uncertainty | G4-1, G4-4 | Apply VLM validation (Tier 2, 20% of boundary-zone images); add ±2% dead-zone around 10% and 50% thresholds | 1 day |
| HW-PRES-G10 | Degraded handwriting absent from DOMINANT training examples | G4-1 through G4-5 | Apply Augraphy degradation augmentations (ink fade, yellowing, foxing) to 10% of DOMINANT examples | 1 day |
| HW-LEG-G05 | Muharaf/PUCIT-OHUL: no legibility annotations — FAIR class undercovered | G4-2, G4-5 | Run full VLM legibility labeling (~28K images total) | 2–3 days compute |
| HW-LEG-G06 | IAM EXCELLENT assumption not validated via VLM | G4-2 | Run VLM on 10% IAM sample (~1,300 images) | 0.5 days |
| HW-LEG-G07 | KHATT OOD provides only 20+ ILLEGIBLE pages — below minimum for reliable per-class F1 (need ≥ 50) | G4-2 | Expand OOD-Handwriting 5a ILLEGIBLE quota from 20 to 50+ pages | 0.5 days |
| HW-LEG-G08 | F1 ≥ 0.72 target exceeds IAA ceiling; revised to ≥ 0.60 | G4-2 | Governance decision (no engineering effort) | 0 days |
| HW-CONT-G07 | TYPED class VLM labeling on RVL-CDIP required; estimated yield 3–8K vs. 6K target | G4-3 | Run VLM on RVL-CDIP letter/memo subset (~40K candidates); filter by TYPED confidence ≥ 0.7 | 2 days |
| HW-CONT-G09 | OOD does not cover MIXED_PRINTED_HW or MIXED_TYPED_HW failure modes | G4-3 | Add OOD sub-source 5e: 50 real MIXED_PRINTED_HW examples from library archives | 1 day |
| HW-PRES-REG-G05 | Pearson r ≥ 0.80 target misleading on bimodal distribution; must add MAE ≤ 0.10 on mid-range holdout as co-primary metric | G4-4 | Governance decision: add MAE on 0.10–0.80 holdout as co-primary metric | 0 days |
| HW-PRES-REG-G07 | COCO-Text bounding box area ratio overestimates handwriting coverage — bias correction not quantified | G4-4 | Compute correction factor from HierText images (both pixel-level and bounding-box annotations available); apply to COCO-Text labels | 1 day |
| HW-PRES-REG-G08 | HierText test split not explicitly held out for G4-4 regression evaluation | G4-4 | Register HierText splits in global split registry before assembly begins | 0.5 days |
| HW-LEG-REG-G03 | Class-to-score mapping formula not empirically validated — current linear interpolation unsupported | G4-5 | Run human rating collection on 300 images spanning all legibility levels; derive mapping empirically from MOS data | 1 day protocol + 2 days annotation |
| HW-LEG-REG-G05 | Pearson r ≥ 0.80 target exceeds IAA ceiling (~0.60–0.65); revised to ≥ 0.55 vs human ratings | G4-5 | Governance decision | 0 days |
| HW-LEG-REG-G07 | VLM circular validation risk — if VLM assigns training labels AND evaluates OOD, Pearson r measures VLM self-consistency | G4-5 | Collect human ratings on ≥ 100 OOD images (KHATT 5a) from ≥ 3 raters for definitive evaluation | 1 day |
| HW-LEG-REG-G08 | VLM score compression — pilot showed 83% of scores in 0.5-range; legibility VLM will compress similarly | G4-5 | Prompt engineering to force full scale use (anchor examples at 1.0 and 5.0 in few-shot prompt); validate distribution before large-scale labeling | 0.5 days |

### P2 Nice-to-Have

| Gap ID | Description | Head(s) | Remediation |
|--------|-------------|---------|-------------|
| HW-PRES-G11 | Historical handwriting (pre-1900 letterforms) absent | All | Source historical manuscript scans (Bentham Papers, IAM-HistDB) |
| HW-PRES-G12 | Engineering form fill-ins underrepresented in MARGINAL/PARTIAL | G4-1 | Expand FUNSD usage; source additional form fill-in datasets |
| HW-PRES-G13 | Stamps/rubber impressions not represented as NONE confounders | G4-1 | Add stamp-only page samples to NONE class |
| HW-LEG-G09 | POOR class underrepresented in Latin-script training data | G4-2 | Source degraded historical handwriting or apply ink-fading augmentation to GOOD samples |
| HW-LEG-G10 | CJK/Devanagari legibility absent from training | G4-2 | Add CASIA-HWDB subset (~500) and IIIT-INDIC subset (~200) to training pool |
| HW-CONT-G12 | CJK handwriting absent from HANDWRITTEN_CURSIVE training | G4-3 | Source CASIA-HWDB or SCUT-HCCDoc; add ~2K–5K examples |
| HW-CONT-G13 | Degraded TYPED class (aged typewriter) absent | G4-3 | Source historical typewriter documents with Augraphy aging augmentation |
| HW-CONT-G15 | If MIXED_TYPED_HW natural acquisition yields < 500 examples, propose schema revision | G4-3 | Conduct data audit after P0 acquisition; if < 500, propose collapsing into single MIXED class |
| HW-PRES-REG-G10 | Construct validity study: pixel-ratio vs. perceptual presence not validated | G4-4 | 50-image pairwise human annotation study |
| HW-PRES-REG-G11 | OOD mid-range coverage insufficient (sub-source 5d only 50 images) | G4-4 | Add 50–100 annotated form fill-in examples to OOD-Handwriting |
| HW-LEG-REG-G12 | Derived-at-inference alternative not evaluated | G4-5 | Prototype legibility_score from legibility_cls output via monotonic mapping; if Pearson r equivalent, retire independent regression head |
| HW-LEG-REG-G13 | Per-script Pearson r breakdown not planned | G4-5 | Compute Pearson r breakdowns by script_code at evaluation time |
| HW-LEG-REG-G15 | Construct validity: legibility_score vs. downstream OCR accuracy not validated | G4-5 | After training, correlate predicted legibility_score with OCR CER on 500-page sample |

### Total Remediation Summary

| Priority | Unique Gaps | Estimated Effort |
|----------|-------------|------------------|
| P0 Blockers | 17 | 8–12 weeks total (G4-3 has serial dependency on G4-1; G4-5 adds regression-specific work on top of G4-2; some shared blockers reduce total) |
| P1 Improvements | 18 | 4–6 additional weeks before evaluation is meaningful |
| P2 Nice-to-Have | 13 | TBD — post-training improvements |

The critical path is: N_A sentinel fix → G4-1 label infrastructure (pixel-ratio + 5-class conversion) → G4-3 presence dependency resolution → MIXED class synthesis → VLM labeling pipelines → assembly subcommand implementation. None of the five G4 heads can reach evaluation-ready status until the N_A sentinel defect is corrected and the G4-1 5-class label conversion is implemented.

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

| Head ID | Head Name | Task | Target Metric | Target Value | Notes |
|---------|-----------|------|--------------|-------------|-------|
| SIG-G4-1 | `presence_cls` | 5-class classification | Macro F1 | ≥ 0.78 | Achievable only after MARGINAL/PARTIAL/SUBSTANTIAL classes are populated; currently 3 of 5 classes have 0 examples |
| SIG-G4-2 | `legibility_cls` | 6-class classification | Macro F1 | ≥ 0.60 | Revised from 0.72; IAA ceiling 60–70%; ILLEGIBLE class at 0 examples will produce F1=0.0 for that class until resolved |
| SIG-G4-3 | `content_type_cls` | 7-class classification | Macro F1 | ≥ 0.72 | MIXED classes at near-zero will produce F1≈0 until synthetic composition is implemented |
| SIG-G4-4 | `presence_reg` | Regression (Gaussian NLL) | Pearson r (primary) + MAE on mid-range holdout (co-primary) | Pearson r ≥ 0.80 + MAE ≤ 0.10 (0.10–0.80 range) | Pearson r ≥ 0.80 alone is spuriously achievable on bimodal data; co-metric MAE on mid-range is required for meaningful evaluation; test set: HierText gold standard (held out) |
| SIG-G4-5 | `legibility_reg` | Regression (Gaussian NLL) | Pearson r vs human MOS | ≥ 0.55 vs human ratings | Revised from 0.80; IAA ceiling ~0.60–0.65 makes 0.80 unachievable; VLM-based Pearson r is secondary metric only (circular validation caveat); human MOS calibration study required before evaluation is meaningful |

### Achieved Results

| Head | Val Metric | Test Metric | Status |
|------|-----------|-------------|--------|
| `presence_cls` | — | — | ❌ Not trained |
| `legibility_cls` | — | — | ❌ Not trained |
| `content_type_cls` | — | — | ❌ Not trained |
| `presence_reg` | — | — | ❌ Not trained |
| `legibility_reg` | — | — | ❌ Not trained |

No G4 head has been trained. Training cannot begin until the 17 P0 blockers are resolved. The estimated unblock timeline is 8–12 weeks of engineering effort.

---

## Related Documents

- **HAR Files**: [sig-g4-presence-cls.md](../../planning/har/sig-g4-presence-cls.md), [sig-g4-legibility-cls.md](../../planning/har/sig-g4-legibility-cls.md), [sig-g4-content-type-cls.md](../../planning/har/sig-g4-content-type-cls.md), [sig-g4-presence-reg.md](../../planning/har/sig-g4-presence-reg.md), [sig-g4-legibility-reg.md](../../planning/har/sig-g4-legibility-reg.md)
- **DDR**: [handwriting_ddr.md](../diversity_reports/handwriting_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)
- **Assembly Script**: [scripts/harmonize_handwriting_labels.py](../../../scripts/harmonize_handwriting_labels.py) (binary presence detection; 5-class conversion required)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-02-23 | Added P0 BLOCKED notice, HAR Assessment section, N_A Sentinel Encoding defect section, ILLEGIBLE Class Gap section with acquisition blockers table; clarified dry-run estimate vs. actual assembled count |
| 1.0.0 | 2026-02-23 | Initial creation from HAR batch E (G4-1 through G4-5) and DDR |
