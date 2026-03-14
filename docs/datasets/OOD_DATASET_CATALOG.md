# OOD Dataset Catalog

> **Status**: ✅ Active | Ideal-State Specification
> **Version**: 3.4.0
> **Created**: 2026-02-21
> **Updated**: 2026-03-06
> **Purpose**: Ideal-state specification document for the OOD holdout evaluation corpus.
> Defines what each OOD image MUST look like, which heads it evaluates, what performance
> targets apply, and what disqualifies an image from inclusion. Acquisition progress is tracked
> separately in `metadata_registry/ood_registry.jsonl`.
>
> **Revision note (v3.4.0, 2026-03-06)**: Updated acquisition progress to match actual registry
> state (9,170 entries, 76.3% of 12K target). Per-category counts, phase statuses, script
> coverage, domain enrichment, and head coverage updated from `ood_registry.jsonl` and
> `OOD_COVERAGE_GAP_REPORT.md`. GT schema note: ML training heads now use DIQA 3-dim fields
> (`iqa_overall`, `iqa_sharpness`, `iqa_color_fidelity`). The OOD registry still carries
> legacy per-degradation fields (`blur_score`, `noise_score`, etc.) for classical IQA detector
> evaluation — these are separate from ML training heads and will be retained alongside the
> DIQA fields.
>
> **Revision note (v3.3.0, 2026-03-06)**: IQA heads transitioned from 6 individual degradation
> heads (blur, noise, contrast, skew, compression, overall_quality) to 3 DIQA-aligned dimensions
> (iqa_overall, iqa_sharpness, iqa_color_fidelity). All IQA head references, OOD labels, GT
> schema, and performance targets updated. Classical IQA detectors remain at runtime; only ML
> training heads changed. See `DEQA_DOC_PSEUDO_LABELING.md`.
>
> **Revision note (v3.0.0, 2026-02-23)**: Updated per 5-model multi-consensus review
> (`CORPUS_OOD_REVIEW_REPORT.md`). Key changes: total target scaled to 12,000–15,000 (from
> 4,900); entropy-based open-set rejection replaced by Energy Score + temperature scaling;
> OOD-Mixed 9a-1/9a-2 re-prioritized to P0; ILLEGIBLE legibility floor revised to 40%.

## Overview

> **Status as of 2026-03-06**: 9,170 images acquired (76.4% of 12K target). Domain enrichment
> complete. 3 heads remain at-risk with 0 labels (`resolution_quality`, `skew_score`,
> `handwriting_legibility_score`); 1 head has low coverage (`handwriting_legibility` at 15 labels);
> 1 head no longer at risk (`code_confidence` at 500 labels). See `OOD_COVERAGE_GAP_REPORT.md`
> for details.

| Category | Current Target | Revised Target | Acquired | Status |
| --- | --- | --- | --- | --- |
| OOD-Script | 600 | 1,520+ | 1,236 | ✅ 81% of revised target |
| OOD-Capture | 600 | 1,200+ | 2,800 | ✅ Exceeds revised target |
| OOD-Degradation | 800 | 1,600+ | 2,930 | ✅ Exceeds revised target |
| OOD-Handwriting | 500 | 1,000+ | 1,990 | ✅ Exceeds revised target |
| OOD-Geometry | 500 | 1,600+ | 1,740 | ✅ Exceeds current target |
| OOD-Resolution | 500 | 800+ | 365 | ⚠️ 46% — labels pending |
| OOD-Domain | 500 | 2,200+ | 959 | ⚠️ 44% of revised target |
| OOD-Code | 200 | 400+ | 500 | ✅ Exceeds revised target |
| OOD-Mixed | 700 | 1,000 (adequate) | 338 | ⚠️ 34% — run last |
| **Total** | **4,900** | **12,000–15,000** | **9,170** | ⚠️ 76.4% of 12K target |

### Per-Head Minimum OOD Coverage

Every model head must have at minimum 50 OOD images covering it; 100+ is the statistical floor
for meaningful evaluation. The table below maps each head to its primary OOD source categories and
flags heads at risk of under-coverage.

| Head | Task | Primary OOD Category | Secondary OOD Category | Min Required | Covered By | Status |
|---|---|---|---|---|---|---|
| MNV4-H1 | orientation_cls | OOD-Geometry (2a symmetric) | OOD-Mixed (9a-1) | 200 | 2a: 300 + 9a-1: 100 | ✅ |
| MNV4-H2 | skew_reg | OOD-Geometry (2b extreme perspective) | OOD-Mixed (9a-2) | 100 | 2b: 100 + 9a-2: 100 | ✅ |
| MNV4-H3 | resolution_quality_reg | OOD-Resolution | OOD-Mixed (9e-1 vector PDF) | 100 | 6a/6b: 500 | ✅ |
| SIG-G1-1 | iqa_overall | OOD-Degradation (4a compound) | OOD-Mixed (9b-1, 9b-3) | 200 | 4a: 500 + 9b compounds | ✅ |
| SIG-G1-2 | iqa_sharpness | OOD-Degradation (4a compound) | OOD-Mixed (9b-1) | 100 | 4a: 500 + 9b-1: 80 | ✅ |
| SIG-G1-3 | iqa_color_fidelity | OOD-Degradation (4a, 4d) | OOD-Mixed (9b-1) | 100 | 4a: 500 + 4d: 100 | ✅ |
| SIG-G2-1 | script_cls (open-set) | OOD-Script (1a–1h reserved) | OOD-Mixed (9c-1, 9c-3) | 200 | 1a–1h: 600 | ✅ |
| SIG-G3-1 | orientation_cls (post-correction) | OOD-Geometry (2a symmetric) | OOD-Mixed (9a-1) | 200 | 2a: 300 + 9a-1: 100 | ✅ |
| SIG-G3-2 | skew_reg (post-correction) | OOD-Geometry (2b extreme) | OOD-Mixed (9a-2) | 100 | 2b: 100 + 9a-2: 100 | ✅ |
| SIG-G4-1 | handwriting_presence_cls | OOD-Handwriting (5a–5d) | OOD-Mixed (9d-1, 9d-3) | 200 | 5a–5d: 500 | ✅ |
| SIG-G4-2 | handwriting_legibility_cls | OOD-Handwriting (5a KHATT ILLEGIBLE) | OOD-Mixed (9d-1) | 100 | 5a ≥20 ILLEGIBLE; 9d-1: 60 | ⚠️ ILLEGIBLE sub-class <100 |
| SIG-G4-3 | handwriting_content_type_cls | OOD-Handwriting (5d specialized) | OOD-Mixed (9d-2 CJK) | 100 | 5d: 50 specialized + 9d-2: 50 | ⚠️ AT RISK (<100 specialized) |
| SIG-G4-4 | presence_reg | OOD-Handwriting (5a–5d) | OOD-Mixed (9d-1, 9d-3) | 100 | 5a–5d: 500 (labeled with presence_score) | ✅ |
| SIG-G4-5 | legibility_reg | OOD-Handwriting (5a KHATT) | OOD-Mixed (9d-1) | 100 | 5a: 200 (must include legibility_score) | ⚠️ AT RISK (depends on KHATT label quality) |
| SIG-G5-1 | capture_method_cls | OOD-Capture (3a–3d) | OOD-Mixed (9b-2 screen) | 200 | 3a–3d: 600 | ✅ |
| SIG-G5-2 | shadow_reg | OOD-Degradation (4c book gutter) | OOD-Mixed (9b-1, 9d-2) | 100 | 4c: 100 + 9b-1: 80 + 9d-2: 50 | ✅ |
| SIG-G5-3 | warping_reg | OOD-Capture (3b ADF curl) | OOD-Mixed (9a-2 perspective) | 100 | 3b: 150 + 9a-2: 100 | ✅ |
| SIG-G5-4 | code_cls | OOD-Code (8a–8c) | OOD-Mixed (9e-2 false positive) | 100 | 8a–8c: 200 | ✅ |
| SIG-G5-5 | resolution_quality_reg | OOD-Resolution (6a–6b) | OOD-Mixed (9e-1 vector) | 100 | 6a/6b: 500 | ✅ |

**Heads requiring remediation:**

- **SIG-G4-2 ILLEGIBLE sub-class**: The 40% performance floor ([^illegible-floor]) means the ILLEGIBLE sub-class needs at minimum 20 ILLEGIBLE-labeled OOD images (5a KHATT). Currently specified as "≥20 pages" in 5a — verify label quality. **Current**: only 15 `handwriting_legibility` labels in registry; human annotation still needed.
- **SIG-G4-3 content_type (specialized)**: 5d provides 50 specialized images and 9d-2 provides 50 CJK content. Ensure all have `handwriting_content_type` labels. If below 100, add 50 images from hand-notation (formula notebooks, engineering drawings) to 5d. **Current**: 550 `handwriting_content_type` labels — OK at category level, verify specialized sub-class count.
- **SIG-G4-5 legibility_reg**: Depends on KHATT images carrying `handwriting_legibility_score` float labels (not just categorical). Verify during KHATT acquisition. **Current**: 0 `handwriting_legibility_score` labels — AT RISK.

**At-risk heads (0 or near-0 labeled images as of 2026-03-06):**

- **skew_score**: 0 labeled — requires trained MobileNetV4 skew head inference
- **handwriting_legibility**: 15 labeled — needs human annotators for IIIT-INDIC/KHATT/CASIA-HWDB2
- **handwriting_legibility_score**: 0 labeled — same as above, continuous score variant
- **resolution_quality**: 0 labeled — run `label_resolution_quality.py` on 365 ood_resolution images
- **code_confidence**: 500 labeled in registry — no longer at risk (was incorrectly listed as at-risk in gap report; `code_confidence` is populated for OOD-Code entries)

---

### Statistical Adequacy Rationale

The original 4,900-image target is insufficient for per-head statistical rigor. A 5-model
consensus review (2026-02-23) determined:

- 4,900 images provides only ±14% confidence interval (CI) at 95% confidence per head
- Minimum 500 images per head for ±7% CI
- 22 heads × 550 images = 12,100 theoretical minimum
- **Target: 12,000–15,000 total images**

If scaling to 15,000 is not feasible before Phase 2 training, all OOD results must be formally
documented as **"directional only"** — trends may be flagged, but statistically rigorous
pass/fail acceptance criteria must NOT be applied until the corpus reaches the 12,000+ target.

## Registry Location

All OOD images are registered in `metadata_registry/ood_registry.jsonl`.
See [OOD Dataset Design](../planning/OOD_DATASET_DESIGN.md) for the complete registry schema
including the full ground-truth field set (19 heads, L2-aligned).

**Reserved scripts** (never in training): Mongolian (Mong), Syriac (Syrc), Georgian (Geor).
See [Script Reservation Policy](../planning/OOD_DATASET_DESIGN.md#script-reservation-policy).

---

## Design Principles

### What Makes an Ideal OOD Image

An image is ideal for the OOD evaluation corpus when it satisfies ALL of the following criteria:

1. **Single, documented OOD dimension**: Differs from the training distribution in exactly one
   clearly defined, documented dimension. For OOD-Mixed, each compound dimension is individually
   labeled so per-dimension performance can be measured.

2. **Fully labeled**: Carries complete ground-truth labels for all 22 heads applicable to its
   category. Partial-label images cannot be used for per-head performance measurement.

3. **Dedup-verified**: Passes SHA256 + pHash dedup (Hamming ≤ 5) against ALL training datasets,
   val splits, and test splits. Any image present in training is disqualified.

4. **Pre-designated**: Has `split_type="ood"` registered in `metadata_registry/ood_registry.jsonl`
   BEFORE any training manifest is generated. Post-hoc OOD designation after training has run
   is invalid — the model may have seen the image during training.

5. **Documented provenance**: Has a recorded source (where it came from), acquisition method,
   and explicit rationale for why it is out-of-distribution relative to training.

6. **Category-specific exclusion criteria met**: Passes the exclusion criteria stated for its
   OOD category (see per-phase specifications below).

### Open-Set Rejection Protocol

The entropy threshold (≥ 0.7) is uncalibrated and must NOT be used as the primary rejection
gate. Modern transformers produce high-confidence (low entropy) wrong predictions on OOD inputs
— a Mongolian document may receive confidence 0.99 on a wrong known-script class.

Required approach:

1. Train model to convergence
2. Apply temperature scaling on held-out calibration set
3. Compute Energy Score: E(x) = -T × log(∑ exp(fᵢ(x)/T))
4. Set rejection threshold on Energy Score distribution
5. Validate on OOD-Script (reserved scripts) as known-negative ground truth

Anywhere this document previously referenced "entropy ≥ 0.7" as a rejection gate, interpret
that as "Energy Score + temperature scaling (calibrated post-training)". Raw softmax entropy
must not be used as the primary OOD detector for SigLIP 2 outputs.

### Why OOD Evaluation Matters

The OOD corpus answers a different question than the standard test set. The test set measures
whether the model generalizes within the training distribution. The OOD corpus measures whether
the model *fails gracefully* on inputs that are demonstrably different from training.

Three failure modes are monitored:

- **Confident-and-wrong**: Model assigns high confidence to an incorrect prediction on OOD input
- **Cascade failure**: MobileNetV4 Stage 1 error corrupts the corrected image passed to SigLIP 2 Stage 2
- **Class void**: Model encounters a class label (e.g., ILLEGIBLE handwriting) absent from training

The `evaluation_pipeline_stage` field on every OOD image records whether the cascade failure
scenario applies: `["mobilenetv4", "siglip2"]` for cascade tests, `["siglip2"]` for single-stage.

---

## Per-Head OOD Performance Targets

The following table defines, for every head, the in-distribution performance target, the OOD
evaluation category that exercises it most directly, the acceptable performance floor on that
category, and the failure threshold that signals a distribution gap requiring remediation.

| Head | Task | In-Dist Target | OOD Category | Acceptable OOD Floor | Failure Threshold |
|------|------|---------------|--------------|---------------------|-------------------|
| MNV4-H1 | orientation_cls | ≥95% accuracy | OOD-Geometry | ≥80% overall; abstention rate ≥85% on `orientation_ambiguous` | <70% overall = distribution gap |
| MNV4-H2 | skew_reg | MAE < 0.5° | OOD-Geometry | MAE < 1.0° on multi-column; abstain if tilt >30° | MAE > 2.0° = failure |
| MNV4-H3 | resolution_quality_reg | MAE < 0.1 | OOD-Resolution | MAE < 0.15 on paradox cases | MAE > 0.25 = model conflating DPI with quality |
| SIG-G1-1 | iqa_overall | VQualA ≥ 0.92 | OOD-Degradation | VQualA ≥ 0.75 on 5+ simultaneous distortions | VQualA < 0.60 = critical IQA gap |
| SIG-G1-2 | iqa_sharpness | VQualA ≥ 0.88 | OOD-Degradation | VQualA ≥ 0.75 on compound distortions | VQualA < 0.60 = critical IQA gap |
| SIG-G1-3 | iqa_color_fidelity | VQualA ≥ 0.85 | OOD-Degradation | VQualA ≥ 0.70 | VQualA < 0.55 = critical IQA gap |
| SIG-G2-1 | script_cls | ≥90% overall, Tibetan ≥80% | OOD-Script | ≥85% on in-dist scripts; open_set trigger for Mong/Syrc/Geor | <75% on in-dist = distribution gap |
| SIG-G3-1 | orientation_cls (post-corr) | ≥98% accuracy | OOD-Geometry | ≥90% (post-correction images expected cleaner) | <80% = post-correction pipeline failure |
| SIG-G3-2 | skew_reg (post-corr) | MAE < 0.3° | OOD-Geometry | MAE < 0.6° | MAE > 1.5° = post-correction skew failure |
| SIG-G4-1 | handwriting_presence_cls | ≥88% | OOD-Handwriting | ≥75% (non-Latin scripts OOD from training) | <60% = P0 handwriting gap |
| SIG-G4-2 | handwriting_legibility_cls | ≥85% | OOD-Handwriting | ≥40% on ILLEGIBLE/POOR (class void in training) [^illegible-floor] | <30% = class void critical |
| SIG-G4-3 | handwriting_content_type_cls | ≥80% | OOD-Handwriting | ≥65% | <50% = content type generalization failure |
| SIG-G4-4 | presence_reg | MAE < 0.15 | OOD-Handwriting | MAE < 0.25 | MAE > 0.40 = regression failure |
| SIG-G4-5 | legibility_reg | MAE < 0.15 | OOD-Handwriting | MAE < 0.25 | MAE > 0.40 = regression failure |
| SIG-G5-1 | capture_method_cls | ≥85% | OOD-Capture | ≥75%; screen recapture sub-class specifically evaluated | <65% = capture gap |
| SIG-G5-2 | shadow_reg | MAE < 0.08 | OOD-Degradation | MAE < 0.15 on book gutter (OOD from training) | MAE > 0.25 = spine shadow gap |
| SIG-G5-3 | warping_reg | MAE < 0.08 | OOD-Capture | MAE < 0.15 | MAE > 0.25 = warping generalization failure |
| SIG-G5-4 | code_cls | >0.5 threshold | OOD-Code | ≥80% recall on IDE/GitHub screenshots | <65% = pipeline generalization failure |
| SIG-G5-5 | resolution_quality_reg | MAE < 0.1 | OOD-Resolution | MAE < 0.15 | MAE > 0.25 = DPI paradox conflation |

**Notes on OOD-Geometry floors (metric segmentation required)**:
The monolithic 80% accuracy floor for MNV4-H1 on OOD-Geometry mixes two fundamentally
different failure modes and must be split into two separate metrics before evaluation:

- **OOD-Abstention-Rate** (symmetric/ambiguous inputs): floor ≥ 85%. Abstaining on ambiguous
  orientation is the safe and correct action.
- **OOD-Correction-Accuracy** (clearly rotated inputs): floor ≥ 88%. Tighter than the
  monolithic 80% because cascade failures on confidently-rotated documents are high risk.
- **OOD-Orientation-Overall** (composite): floor ≥ 87% (replaces monolithic 80% floor).

An 80% overall score can mask 100% correct abstention but 50% failed correction — the
monolithic floor must not be used as an acceptance criterion.

**Notes on ILLEGIBLE floor** [^illegible-floor]:
Revised from 65% → 40%: The 65% floor assumed the model had training examples for the
ILLEGIBLE class. ILLEGIBLE has 0 training examples as of 2026-02-21. The 40% floor reflects
open-set recognition baseline performance, not trained classification. Re-evaluate once
≥5K ILLEGIBLE handwriting samples are acquired and the model has been retrained.

---

## Training Dataset Dependencies

Each OOD category evaluates robustness in conditions not represented in its corresponding training dataset. The canonical three-way mapping (Head ↔ Training Dataset ↔ OOD Category) lives in [TRAINING_DATASET_QUICK_REFERENCE.md — Head ↔ Dataset ↔ OOD Cross-Reference](TRAINING_DATASET_QUICK_REFERENCE.md#head--dataset--ood-cross-reference). The table below summarises at the category level for acquisition planning.

| OOD Category | Training Dataset(s) | # | Heads Evaluated | Gap / Stress Scenario |
|---|---|---|---|---|
| **OOD-Script** | script-detection | 5 | SIG-G2-1 | Reserved scripts (Mong/Syrc/Geor) never seen; open-set rejection; Phase 2 preview scripts (Grek/Armn/Ethi) |
| **OOD-Geometry** | orientation, skew | 1, 2 | MNV4-H1, MNV4-H2, SIG-G3-1, SIG-G3-2 | 0°/180° disambiguation on symmetric docs; extreme perspective; Japanese TTB convention (labeled 0°, not 270°) |
| **OOD-Capture** | capture-method, warping | 7, 9 | SIG-G5-1, SIG-G5-3 | Screen recapture moiré/aliasing (no training analog); ADF curl artifacts; 4th-gen photocopy degradation |
| **OOD-Degradation** | iqa, shadow | 4, 8 | SIG-G1-1, SIG-G1-2, SIG-G1-3 (DIQA 3-dim), SIG-G5-2 | ≥5 simultaneous distortion types; book gutter shadow gradient not in sd7k; binarized `color_mode` absent |
| **OOD-Handwriting** | handwriting | 6 | SIG-G4-1, SIG-G4-2, SIG-G4-3, SIG-G4-4, SIG-G4-5 | ILLEGIBLE class absent from training; non-Latin handwriting (Arab/CJK/Deva); `specialized` content type |
| **OOD-Resolution** | resolution-quality | 3 | MNV4-H3, SIG-G5-5 | Born-digital low-DPI paradox (large font → high char-height at 72 DPI); 2×/4× upscale artifact detection |
| **OOD-Domain** | script-detection (secondary) | 5 | All 22 heads (robustness) | Novel domain combos: government forms, religious texts, thermal receipts — cross-domain generalization |
| **OOD-Code** | code-detection | 10 | SIG-G5-4 | IDE screenshots, mixed prose+code (arXiv/Jupyter), terminal output — outside generation-script distribution |
| **OOD-Mixed** | orientation, skew, iqa, shadow, warping | 1, 2, 4, 8, 9 | MNV4-H1, MNV4-H2, SIG-G1-1, SIG-G1-2, SIG-G1-3 (DIQA 3-dim), SIG-G3-1, SIG-G3-2, SIG-G5-2, SIG-G5-3 | Cascade failures: Mongolian TTB + aged + perspective; CJK HW + gutter shadow; binarized + extreme compression |

> **Note**: OOD-Domain tests all 22 heads for general robustness. Its secondary link to #5 (script-detection) reflects the Fraktur/Ottoman Arabic sub-sources in Phase 1 of acquisition.

---

## Acquisition Roadmap

### Synthetic Generation Scripts (Phase 3 Implementation)

Scripts in `scripts/` provide synthetic OOD coverage while manual acquisitions are pending.
All scripts source from DocLayNet train split (CDLA-Permissive-1.0) unless noted, apply
SHA256 + pHash dedup (Hamming ≤ 5), and register to `metadata_registry/ood_registry.jsonl`.

> **Execution order**: Run all single-category scripts first (Recipes 1–12 in any order),
> then run `generate_ood_mixed.py` **last** after all categories have reached ≥90% of target.

| Script | Recipe(s) | OOD Category | Catalog Section | Target |
|--------|-----------|--------------|-----------------|--------|
| `generate_ood_symmetric.py` | 1 | `ood_geometry` | §2a | 500 |
| `generate_ood_extreme_perspective.py` | 2 | `ood_geometry` | §2b | 500 |
| `generate_ood_compound_geometry.py` | 3 | `ood_geometry` | §2d (new) | 500 |
| `generate_ood_compound_distortion.py` | 5 | `ood_degradation` | §4a | 500 |
| `generate_ood_screen_recapture.py` | 6 | `ood_degradation`, `ood_capture` | §3a | 300 |
| `generate_ood_fax_artifacts.py` | 7 | `ood_degradation`, `ood_capture` | §4e (new) | 200 |
| `generate_ood_multidpi.py` | 9+10 | `ood_resolution` | §6a, §6b | 535 |
| `generate_ood_code_screenshots.py` | 11+12 | `ood_code` | §8a, §8b | 424 |
| `generate_ood_mixed.py` | 13 | `ood_mixed` (stacked) | Phase 9 | 762 |

**Total synthetic target: 4,221 images** across all categories (762 mixed is additive; run last).

Dry-run any script with `uv run python scripts/generate_ood_X.py --dry-run` before executing.
All scripts accept `--output-dir` and `--registry` to override defaults if needed.

---

### Phase 1: Script OOD (OOD-Script) — P0

**Target: 600 images total across 8 sub-sources** | **Acquired: 1,236** ✅ exceeds current target

> **Specification:** The ideal OOD-Script set contains images that exercise script classes that
> are *either permanently reserved from training* (Mongolian/Mong, Syriac/Syrc, Georgian/Geor)
> *or use font variations significantly outside the training font families*. These images test
> whether the script head (SIG-G2-1) correctly rejects unseen scripts using Energy Score +
> temperature scaling (calibrated post-training) and handles in-distribution scripts rendered in
> unusual typography. Performance target: ≥ 85% accuracy on in-distribution scripts;
> Energy Score-based open-set rejection for reserved scripts (threshold calibrated
> post-training — see Open-Set Rejection Protocol). Exclusion criteria: any image whose SHA256
> or pHash (Hamming ≤ 5) matches any training manifest entry; any image already in a training
> split of the orientation or skew datasets (Phase 1b Mongolian subset from v3 must be
> pre-designated `split_type="ood"` before manifest generation).

#### 1a. Mongolian real (MTHv2) — target: 100 images

- Source: Mongolian Traditional Heritage dataset (MTHv2)
- Acquisition: Download from public repository
- Labels required: `script=Mong`, `open_set=true`, `orientation=0`, `text_direction=ttb`,
  `capture_method=scanner_flatbed`, `document_age=modern`
- Cross-category: OOD-Geometry (TTB vertical orientation stress)
- Dedup required: Against all training datasets (SHA256 + pHash, Hamming ≤ 5)
- Status: ⏳ Pending — no Mong script entries in registry yet

#### 1b. Mongolian synth-v3 extract — target: 50 images

- Source: Extract from `gs://image_detection_b/synth_multiscript_v3/` — Mongolian subset
- **Critical**: Must verify Mongolian images exist in v3; if so, mark `split_type="ood"` BEFORE
  any training manifest is generated. These images may not be used in training.
- Labels required: `script=Mong`, `open_set=true`, `orientation` (from sidecar),
  `text_direction=ttb`, `capture_method=synthetic`
- Cross-category: OOD-Geometry
- Status: ⏳ Pending — requires v3 pool audit for Mongolian presence

#### 1c. Syriac manuscripts — target: 120 images

- Source: SANA corpus ([ufal.mff.cuni.cz/sana](https://ufal.mff.cuni.cz/sana)), OpenITI Syriac subset
- Acquisition: Download + sample 120 pages
- Labels required: `script=Syrc`, `open_set=true`, `orientation`, `text_direction=rtl`,
  `capture_method=scanner_flatbed`, `document_age=historical`
- Cross-category: OOD-Geometry (RTL orientation disambiguation)
- Dedup required: Against Arabic training datasets (similar script family)
- Status: ⏳ Pending

#### 1d. Georgian archives — target: 100 images

- Source: National Parliamentary Library of Georgia (nplib.ge), Wikimedia Commons
- Acquisition: Download + curate 100 pages
- Labels required: `script=Geor`, `open_set=true`, `orientation=0`, `text_direction=ltr`,
  `document_age=modern` or `historical`
- Status: ⏳ Pending

#### 1e. Historical Fraktur — target: 50 images

- Source: Project Gutenberg + Wikimedia Commons (public domain German texts pre-1900)
- Acquisition: Manual curation + dedup against RVL-CDIP (critical — overlap risk)
- Labels required: `script=Latn`, `open_set=false`, `capture_method=scanner_flatbed`,
  `document_age=historical`
- Cross-category: OOD-Domain
- **Warning**: Must run SHA256 + pHash dedup against RVL-CDIP before registration
- Status: ⏳ Pending

#### 1f. Ottoman Arabic — target: 30 images

- Source: Public domain Ottoman archives (Library of Congress, open collections)
- Acquisition: Manual curation + dedup against Arabic training datasets
- Labels required: `script=Arab`, `open_set=false`, `capture_method=scanner_flatbed`,
  `document_age=historical`, `text_direction=rtl`
- Cross-category: OOD-Domain
- Status: ⏳ Pending

#### 1g. Phase 2 preview scripts — target: 75 images (~25 each: Greek, Armenian, Ethiopic)

- Purpose: Evaluate open-set rejection behavior before Phase 2 training expands to these scripts
- Source: Unicode consortium samples, national digital libraries, linguistic archives
- Labels required: `script=Grek/Armn/Ethi`, `open_set=true`, `orientation`
- Note: Once Phase 2 training includes these scripts, move to OOD-Domain or retire
- Status: ⏳ Pending

#### 1h. Font variation (decorative fonts in trained scripts) — target: 75 images

- Purpose: Test whether script head overfits to specific font shapes vs. true script features
- Sources:

  - Ornamental/calligraphic Latin fonts rendered on standard document templates
  - Gothic/Blackletter English digital typefaces (modern rendering, not historical scans)
  - CJK brush-style digital fonts (e.g., FZShuTi, HanziPen)
  - Devanagari ornate display fonts

- Labels required: `script=Latn/Hans/Jpan/Deva` (as appropriate), `open_set=false`,
  `capture_method=born_digital`
- Acquisition: Render via Python (Pillow + curated font files) at standard DPIs
- Status: ✅ 75 images registered via `synthetic_pillow_render`

---

### Phase 2: Geometry OOD (OOD-Geometry) — P0

**Target: 500 images total** | **Acquired: 1,740** ✅ exceeds revised target

> **Specification:** The ideal OOD-Geometry set contains images where *orientation or skew
> estimation is either inherently ambiguous or involves non-Latin orientation conventions*.
> Specifically: symmetric/blank documents where there is no correct orientation (tests abstention
> behavior, target rate ≥ 85%); extreme perspective tilt >30° where skew measurement is
> unreliable; and Japanese vertical text which is labeled as `orientation=0` in training (tests
> that the TTB convention is preserved under the pipeline cascade). Performance targets:
> MNV4-H1 ≥ 80%; MNV4-H2 MAE < 1.0° on multi-column; SIG-G3-1 ≥ 90%; SIG-G3-2 MAE < 0.6°.
> Exclusion criteria: images from DocLayNet used in training without dedup check; Mongolian TTB
> images (reserved — use OOD-Script or OOD-Mixed instead).

#### 2a. Symmetric documents — target: 300 images

- Source: Wikipedia article screenshots, government form templates, non-DocLayNet cover pages
- **IMPORTANT**: Must NOT use DocLayNet directly — it is a training source. Use a fresh crawl
  or Wikipedia screenshots that pass dedup against DocLayNet.
- Acquisition: Automated screenshot pipeline + human verification of visual symmetry
- Labels required: `orientation` (human-verified), `script=Latn`,
  `capture_method=born_digital`
- Purpose: Test 0°/180° disambiguation when document has no strong orientation cue
- Cross-category: OOD-Mixed (with TTB Mongolian for cascade failure coverage)
- Dedup required: Against DocLayNet (high overlap risk for cover/title pages)
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]` (cascade failure test)
- **Synthetic coverage**: `scripts/generate_ood_symmetric.py` (Recipe 1) — 500 images derived
  from DocLayNet train pages via center-crop (y: 20–80%, x: 10–90%) + 0°/90°/180°/270° rotation.
  Provides synthetic interim coverage at 4× the manual target while external screenshots are pending.
- Status: ✅ 700 synthetic images registered | ⏳ Manual acquisition pending

#### 2b. Extreme perspective — target: 100 images

- Source: Internal photography (document photographed at >30° tilt)
- Acquisition: Physical collection — photograph documents at steep angles (3 tilt axes)
- Labels required: `skew_angle_degrees` (measured), `orientation`, `warping_type=perspective`,
  `capture_method=camera_smartphone`
- **Synthetic coverage**: `scripts/generate_ood_extreme_perspective.py` (Recipe 2, P0) — 500
  images with ≥15% corner displacement applied to DocLayNet pages, simulating extreme tilt.
  Synthetic extreme-perspective is a reliable analog until physical photography is available.
- Status: ✅ 900 images registered (local_dataset_full_pool) | ⏳ Manual photography pending

#### 2c. Japanese vertical text — target: 100 images

- Source: NDL Digital Collection (National Diet Library Japan), public domain Japanese archives
- Purpose: Japanese vertical text is labeled as `orientation=0` in training (non-standard
  convention). OOD coverage verifies the model handles this correctly without confusing TTB
  with rotated documents.
- Labels required: `script=Jpan`, `orientation=0`, `text_direction=ttb`,
  `capture_method=scanner_flatbed`
- Dedup required: Against synth-multiscript-v3 (Jpan samples present in training)
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]`
- Status: ⏳ Pending

#### 2d. Compound skew + page curl (synthetic) — target: 500 images

- Source: DocLayNet train split — not used in OOD-Geometry manual targets above
- **Implementation**: `scripts/generate_ood_compound_geometry.py` (Recipe 3, P1)
- Transform pipeline:
  1. Random skew ±[3°, 10°] applied via affine transform (`cv2.warpAffine`)
  2. Sinusoidal page-curl remap: `x'(x,y) = x + amplitude * sin(π * y / H)`,
     amplitude ∈ [12, 30] px via `cv2.remap`
- Labels generated: `skew_angle_degrees`, `warping_severity` ([0.35, 0.65] range),
  `warping_type=page_curl`, `capture_method=born_digital`
- Purpose: Simultaneously stresses MNV4-H2 (skew regression) and SIG-G5-3 (warping regression)
  with a compound geometric distortion not present in the manual 2a–2c sub-sources above
- Seed: `0xDEADBEEF_0DD5AFEC ^ 0x03 = 0x0DD5AFEF`
- `ood_categories`: `["ood_geometry"]`
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]`
- Status: ✅ Synthetic script ready (P1) | No manual acquisition equivalent

---

### Phase 3: Capture OOD (OOD-Capture) — P0

**Target: 600 images total** | **Acquired: 2,800** ✅ exceeds revised target

> **Specification:** The ideal OOD-Capture set contains images captured by *methods that generate
> artifacts absent from the training capture distribution*: screen recapture moiré/RGB aliasing
> (no training analog), ADF scanner curl artifacts (heuristic-labeled in training but not fully
> represented), and iterative photocopy degradation beyond what single-pass Augraphy generates.
> These test whether SIG-G5-1 (capture_method_cls) and SIG-G5-3 (warping_reg) generalize beyond
> training. Performance targets: SIG-G5-1 ≥ 75% on screen recapture class; SIG-G5-3 MAE < 0.15.
> Exclusion criteria: screen recapture images with moiré below perceptible threshold (not
> genuinely OOD); ADF images that could plausibly be classified as flatbed.

#### 3a. Screen recaptures — target: 200 images

- Source: Internal generation — photograph LCD/OLED/E-ink screen displaying documents
- Acquisition: Physical collection (3 device types × 3 angles × 20+ documents)
- Labels required: `capture_method=camera_smartphone`, IQA labels (blur, noise, contrast),
  `color_mode=color`
- Purpose: Unique moiré/RGB aliasing artifacts not in any training dataset
- Cross-category: OOD-Mixed (screen recapture + RTL document)
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]` (cascade: moiré degrades SigLIP)
- **Synthetic coverage**: `scripts/generate_ood_screen_recapture.py` (Recipe 6, P1) — 300 images.
  Pipeline: downsample to 40–55% → sinusoidal RGB moiré overlay (freq 0.08–0.18 c/px, angle 5–15°) →
  perspective tilt 15–25° → bicubic upsample. `capture_method=screen_recapture`.
  Synthetic moiré is structurally equivalent to physical screen recapture artifacts.
- Status: ✅ 300 synthetic + 1,000 local_dataset_train_split + 900 full_pool + 300 local_copy + 200 augraphy registered | ⏳ Physical collection pending

#### 3b. ADF scanner with curl artifacts — target: 150 images

- Source: Internal scanning with Fujitsu ScanSnap or equivalent ADF scanner
- Acquisition: Scan documents with intentional page curl, skew, and edge feed artifacts
- Labels required: `capture_method=scanner_adf`, `warping_type=page_curl`,
  `warping_severity`, `skew_angle_degrees`
- Status: ⏳ Pending

#### 3c. 4th-generation photocopies — target: 150 images

- Source: Iterative photocopy simulation via Augraphy (`photocopy` augmentation, 4 passes)
- Acquisition: Script generation from training-excluded source documents
- Labels required: `capture_method=scanner_flatbed`, IQA labels (noise, contrast, compression),
  `document_age=aged`
- Status: ⏳ Pending

#### 3d. High-speed production scanner — target: 100 images

- Source: Internal scanning on production-grade document scanner (Kodak, Canon DR series)
- Acquisition: Scan at 300+ ppm with high-speed feed settings
- Labels required: `capture_method=scanner_flatbed`, IQA labels, `color_mode`
- Status: ⏳ Pending

---

### Phase 4: Degradation OOD (OOD-Degradation) — P0

**Target: 800 images total** | **Acquired: 2,930** ✅ exceeds revised target

> **Specification:** The ideal OOD-Degradation set contains images with *degradation combinations
> that exceed what single-distortion IQA training covers* — specifically, compound distortions
> (≥ 5 simultaneous types), book gutter shadow gradients (absent from sd7k flat-document training
> data), binarized 1-bit documents where shadow_severity is unmeasurable, and bleed-through with
> bimodal backgrounds. These test all 3 DIQA-aligned IQA heads (SIG-G1-1 to G1-3: iqa_overall,
> iqa_sharpness, iqa_color) and the shadow head
> (SIG-G5-2). Performance targets: VQualA ≥ 0.80 on compound 5+ distortions; shadow MAE < 0.15
> on book gutter. Exclusion criteria: compound images assembled from the same Augraphy pipeline
> used in IQA training (must use a *different* augmentation engine to avoid correlation);
> binarized images with shadow_severity labeled by SSIM (SSIM labels are permanently invalid for
> shadow/warping severity).

#### 4a. Multiply-distorted (≥5 simultaneous types) — target: 500 images

- Source: Augraphy with ≥5 simultaneous distortion types applied to training-excluded documents
- Distortion stack: gutter-shadow + page_curl + defocus blur + noise + JPEG compression
- Labels required: 3-dim DIQA labels (`iqa_overall`, `iqa_sharpness`, `iqa_color_fidelity`),
  `shadow_severity`, `warping_severity`, `shadow_type`, `warping_type`
- IQA labels: DIQA-5000 GT where available (weight=1.0); DeQA-Doc pseudo-labels with OOD-gated
  sample weights for remaining images. Classical IQA detectors provide supplementary per-issue
  signals at runtime but are not used as training labels.
- **Synthetic coverage**: `scripts/generate_ood_compound_distortion.py` (Recipe 5, P0) — 500
  images. Uses OpenCV-native distortion stacking (NOT the same Augraphy pipeline as IQA training),
  satisfying the mandatory different-augmentation-engine requirement above.
- Status: ✅ 500 albumentations_compound + 1,000 synthetic_generation registered | ⏳ Human IQA annotation pending

#### 4b. Watermarked documents — target: 100 images

- Source: Public government forms with official watermarks + synthetic watermark overlay
- Labels required: `watermark_severity` (0.0–1.0, human-labeled)
- Status: ✅ 100 images registered via `pil_watermark` (100 `watermark_severity` labels)

#### 4c. Book gutter shadow (hard shadow gradient) — target: 100 images

- Source: Internal photography of bound books photographed open-flat
- Purpose: sd7k training data covers flat-document shadows only; gutter shadows have a
  distinct gradient curve not present in training data
- Labels required: `shadow_severity`, `shadow_type=hard`, `warping_type=page_curl`
- Cross-category: OOD-Mixed
- Status: ✅ 80 `synthetic_composite_shadow` registered (580 total shadow_severity labels in registry)

#### 4d. Binarized (1-bit) documents — target: 100 images

- Source: Archival 1-bit TIFF scans from public domain collections + Sauvola binarization
  applied to training-excluded grayscale images
- Labels required: `color_mode=binarized`, IQA labels, `capture_method`
- Purpose: `image_properties.color_mode=binarized` not present in current IQA training data
- Status: ⏳ Pending

#### 4e. Fax artifacts (synthetic) — target: 200 images

- Source: DocLayNet train split
- **Implementation**: `scripts/generate_ood_fax_artifacts.py` (Recipe 7, P2)
- Transform pipeline (applied to each source page):
  1. Grayscale conversion
  2. Gaussian pre-blur (3×3 or 5×5) — simulates analogue bandwidth limiting
  3. Floyd-Steinberg error-diffusion dithering → 1-bit halftone (values in {0, 255})
  4. Horizontal line noise: random dropout/dark/gray bands (1–4 px wide, 1–4% of image height)
  5. Contrast reduction (factor 0.55–0.75) → moderate mid-gray flatten
  6. Convert back to 3-channel grayscale
- Labels generated: `capture_method=fax`, `color_mode=binarized`,
  `iqa_overall` (DeQA-Doc pseudo-label), `iqa_sharpness`, `iqa_color_fidelity`
- Wild condition: `fax_artifacts` — ~0% training coverage; distinct halftone texture not
  present in any IQA training dataset
- Cross-category: Overlap with 4d (binarized) — both set `color_mode=binarized`
- `ood_categories`: `["ood_degradation", "ood_capture"]`
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]`
- Seed: `0xDEADBEEF_0DD5AFEC ^ 0x07 = 0x0DD5AFEB`
- Status: ✅ Synthetic script ready (P2) | No manual acquisition equivalent

---

### Phase 5: Handwriting OOD (OOD-Handwriting) — P0

**Target: 500 images total** | **Acquired: 1,990** ✅ exceeds revised target

> **Specification:** The ideal OOD-Handwriting set contains images with *handwriting from script
> families absent or severely underrepresented in training* (Arabic cursive, CJK full-page,
> Devanagari) and images where *legibility is ILLEGIBLE* (a class that is a class void in current
> training data). These test all 5 Group 4 heads (SIG-G4-1 through G4-5). Performance targets:
> presence classification ≥ 75%; ILLEGIBLE/POOR legibility ≥ 40% accuracy [^illegible-floor].
> Exclusion criteria: images where handwriting is mixed with substantial printed text but not
> labeled accordingly; KHATT/CASIA-HWDB images already designated for training splits.
>
> [^illegible-floor]: **Revised from 65% → 40%**: The 65% floor assumed the model had training
> examples for the ILLEGIBLE class. ILLEGIBLE has 0 training examples as of 2026-02-21. The 40%
> floor reflects open-set recognition baseline performance, not trained classification. This floor
> must be re-evaluated once ≥5K ILLEGIBLE samples are acquired and training is complete.

#### 5a. KHATT Arabic cursive — target: 200 images

- Source: KHATT dataset ([khatt.ideas2serve.net](https://khatt.ideas2serve.net/))
- Acquisition: Download + sample 200 pages not in training split
- Labels required: `handwriting_presence=SUBSTANTIAL`, `handwriting_presence_score`,
  `handwriting_legibility` (including FAIR/POOR/ILLEGIBLE cases), `handwriting_content_type=prose`,
  `handwriting_script=Arab` (L2 field), `text_direction=rtl`
- **ILLEGIBLE coverage**: Select 20+ pages with `handwriting_legibility=ILLEGIBLE` to cover
  this class that is absent from training data
- Dedup required: Against any Arabic handwriting training data
- Status: ✅ ~400 KHATT images registered via `local_dataset_copy` | ⚠️ `handwriting_legibility` labels still needed (only 15 in registry)

#### 5b. CASIA-HWDB CJK handwritten — target: 150 images

- Source: NLPR CASIA database (request form required at [nlpr.ia.ac.cn/databases](http://nlpr.ia.ac.cn/databases/))
- Fallback if access denied: SCUT-HCCDoc dataset (open access Chinese handwritten documents)
- Acquisition: Download + sample 150 pages not in training split
- Labels required: `handwriting_presence=SUBSTANTIAL`, `handwriting_presence_score`,
  `handwriting_legibility`, `handwriting_content_type`
- Status: ✅ ~50 CASIA-HWDB2 images registered via `local_dataset_copy` | ⏳ Remaining 100 pending

#### 5c. IIIT-INDIC Devanagari handwritten — target: 100 images

- Source: IIIT-INDIC dataset (public access)
- Acquisition: Download + sample 100 pages
- Labels required: `handwriting_presence=SUBSTANTIAL`, `script=Deva`, `text_direction=ltr`
- Status: ✅ ~500 IIIT-INDIC images registered via `local_dataset_copy`

#### 5d. Specialized content handwriting — target: 50 images

- Source: Mathematical hand-notation (formula notebooks, engineering drawings) from public
  domain archives
- Purpose: `handwriting_content_type=specialized` class not covered in any training HW dataset
- Labels required: `handwriting_content_type=specialized`, `handwriting_presence`
- Status: ⏳ Pending

---

### Phase 6: Resolution OOD (OOD-Resolution) — P0

**Target: 500 images total** | **Acquired: 365** ⚠️ 73% of current target, labels pending

> **Specification:** The ideal OOD-Resolution set contains images that expose the *resolution
> paradox*: cases where the character height measurement signal is artificially inflated or where
> DPI metadata is misleading. Specifically: born-digital PDFs rendered at 72/150/300 DPI where
> visual quality is constant but char_height varies with DPI; and bicubic-upscaled rasters where
> char_height is inflated post-upscaling. These test MNV4-H3 and SIG-G5-5. Performance targets:
> MAE < 0.15 on paradox cases; model must not conflate DPI with perceptual quality (i.e.,
> born-digital at 72 DPI must not be rated lower than raster at 72 DPI with genuinely small text).
> Exclusion criteria: any pages from DIQA-5000 (in training); pages with text too small to
> distinguish resolution paradox from genuine low-resolution.

#### 6a. Vector PDF at 3 DPIs — target: 300 images

- Source: DocLayNet born-digital PDFs (already available locally)
- **Note**: DocLayNet IS used in training. Must run SHA256 + pHash dedup of rendered images
  against training manifests. Use pages/documents not in training split.
- Acquisition: Render each at 72 DPI, 150 DPI, 300 DPI using PyMuPDF (100 pages × 3 DPIs)
- Labels required: `capture_method=born_digital`, `resolution_quality` (measured char height),
  `color_mode`
- Purpose: Vector PDFs rendered at low DPI create a misleading resolution signal (high char
  height possible at 72 DPI from large fonts, but low effective resolution)
- **Synthetic coverage**: `scripts/generate_ood_multidpi.py` (Recipe 9, P2) — 300 images.
  Selects 100 DocLayNet train pages and downsamples each to 72 DPI (`very_low`), 100 DPI
  (`very_low`), and 150 DPI (`low`) via `cv2.INTER_AREA` resize (scale = target_dpi / 300).
  Dedup run against registry before registration. Source pages not in training split only.
- Status: ✅ 12 images registered (4 each at 72/150/300 DPI via `doclaynet_local_pdf_*`) | ⏳ Remaining 288 pending full PyMuPDF pipeline

#### 6b. Upscaled rasters — target: 200 images

- Source: OHR-Bench test set or RealDAE subset — NOT DIQA-5000 (DIQA-5000 is in training)
- Acquisition: Apply 2× and 4× bicubic upscaling (100 images × 2 upscale factors)
- Labels required: `resolution_quality` (measured on original before upscaling),
  `capture_method` (as original), `color_mode`
- Labels: Include `upscale_factor` (2 or 4) as a custom field for analysis
- **Source restriction**: DIQA-5000 must not be used — it is in training. Confirm OHR-Bench
  test split is not included in any training manifest before use.
- **Synthetic coverage**: `scripts/generate_ood_multidpi.py` (Recipe 10, P2) — 235 images.
  Takes the 72-DPI downsampled outputs from Recipe 9 and bicubic-upsamples back to 300-DPI
  equivalent size (`cv2.INTER_CUBIC`, scale = 300/72 ≈ 4.17×). Labels as
  `resolution_quality=upscaled_artifact`. Source images are DocLayNet-derived (not OHR-Bench as
  originally specified); dedup handles any training overlap. Supplement with OHR-Bench once
  available for the non-synthetic upscale artifact coverage this section originally intended.
- Status: ✅ 353 images registered (199 `ohr_bench_bicubic_2x` + 154 `ohr_bench_bicubic_4x`) | ⚠️ `resolution_quality` GT labels still pending (run `label_resolution_quality.py`)

---

### Phase 7: Domain OOD (OOD-Domain) — P1 (smoke test is P0)

**Target: 500 images total** (revised target: 2,200+ for statistical validity) | **Acquired: 959** ⚠️ 44% of revised target

> **Specification:** The ideal OOD-Domain set contains images from *document domains that are
> absent or severely underrepresented in the training domain distribution*: non-English government
> administrative forms, religious/liturgical texts (Hebrew RTL, Arabic Quran, Sanskrit Devanagari),
> and technical manuals with dense mixed content. These test general backbone robustness for all
> 22 heads, with script (SIG-G2-1), IQA Group 1, and orientation heads (MNV4-H1, SIG-G3-1) as
> primary evaluations. Performance target: no head should degrade more than 10% relative to
> in-distribution performance. Exclusion criteria: government forms containing PII — use only
> blank/template forms or explicitly de-identified images.

### Pre-Acquisition Smoke Test (Required First Step) — P0

Before full OOD-Domain acquisition, run a domain smoke test:

- 100 ArXiv PDF pages (freely available via arXiv API)
- Run all 22 heads at inference
- Establish baseline coverage and failure modes
- Required gate before declaring OOD-Domain acquisition viable
- Status: ✅ 99 ArXiv PDF pages registered via `arxiv_pdf_render` — smoke test coverage available

This is re-prioritized to P0 (from P1) per corpus review 2026-02-21: 100 ArXiv PDFs are
trivially acquirable and test all 22 heads simultaneously on a novel born-digital domain.
This unblocks domain coverage analysis before committing to the full 500-image acquisition.

#### 7a. Non-English government forms — target: 250 images

- Source: Public domain government forms in non-English jurisdictions (EU, India, Japan, etc.)
- Acquisition: Curate 250 images across domain types and languages
- Labels required: All applicable heads; `document_age=modern`
- PII considerations: Government forms often contain PII. Use blank/template forms or
  officially released blank versions only. If real filled forms are used, must be explicitly
  de-identified. Alternatively, use synthetic facsimiles generated from templates.
- Status: ⏳ Pending

#### 7b. Religious texts — target: 150 images

- Source: Public domain religious manuscripts, Bible societies open digitization projects,
  Buddhist canon digital archives
- Labels required: All applicable heads; `document_age` (modern/historical varies)
- Status: ⏳ Pending

#### 7c. Technical manuals and receipts — target: 100 images

- Source: Open-source hardware manuals, thermal receipt facsimiles
- Labels required: All applicable heads; `capture_method`, IQA labels
- Purpose: Receipt thermal fade and bleed-through artifacts not in training IQA data
- Status: ⏳ Pending

---

### Phase 8: Code OOD (OOD-Code) — P0

**Target: 200 images total** | **Acquired: 500** ✅ exceeds revised target

> **Specification:** The ideal OOD-Code set contains code images from *rendering environments
> outside the synthetic PIL+Pygments pipeline used in training*: IDE/GitHub screenshots with UI
> chrome (scrollbars, line numbers, syntax highlighting), mixed prose+code pages from arXiv or
> Jupyter exports (boundary cases 0.3–0.7 code confidence), and terminal/shell output. These
> test SIG-G5-4 (code_cls) exclusively. Performance targets: recall ≥ 80% on IDE/GitHub
> screenshots; false positive rate < 15% on non-code mixed content. Exclusion criteria:
> screenshots of empty editors; images where code is < 10% of content but labeled
> code_confidence > 0.5.

Purpose: The SigLIP `code_confidence` head (Group 5) has zero OOD coverage in the original
design. This category provides dedicated code document evaluation.

#### 8a. Source code screenshots — target: 100 images

- Source: GitHub repository screenshots, VS Code window captures, IDE screenshots
- Acquisition: Automated screenshot pipeline across 5+ programming languages
- Labels required: `code_confidence=1.0` (human-labeled), `capture_method=born_digital` or
  `camera_smartphone`, `color_mode=color`, IQA labels
- **Synthetic coverage**: `scripts/generate_ood_code_screenshots.py` (Recipe 11, P1) — 300
  images. Uses Pygments `ImageFormatter` (with `friendly`/`monokai` themes) or PIL fallback to
  render Python source files from the project's `src/` directory as syntax-highlighted images.
  Variations: light/dark theme, font sizes 10/12/14 pt, with/without line numbers.
  Source is the project's own codebase (not IDE screenshots as originally specified); provides
  clean synthetic coverage at 3× the manual target while external IDE screenshots are pending.
- Status: ✅ 424 synthetic images registered (`synthetic_generation`) + 4 Playwright screenshots | ⏳ External IDE screenshots pending

#### 8b. Mixed prose + code documents — target: 60 images

- Source: arXiv technical papers with large code blocks, Jupyter notebook exports
- Acquisition: Render PDF pages containing both prose and code sections
- Labels required: `code_confidence` (0.3–0.7 range, human-labeled), `capture_method=born_digital`
- **Synthetic coverage**: `scripts/generate_ood_code_screenshots.py` (Recipe 12, P1) — 124
  images. Renders Markdown files from the project's `docs/` directory as styled images,
  detecting fenced code blocks (` ``` `) and rendering them with a shaded background.
  `code_confidence` is set by code-block area ratio: 0.0–0.3 (prose-dominant), 0.3–0.5
  (mixed), 0.5–1.0 (code-dominant). Good boundary-case coverage for the 0.3–0.7 confidence range.
- Status: ✅ 46 `arxiv_pdf_code_page` images registered | ⏳ Jupyter pipeline pending

#### 8c. Terminal/console output — target: 40 images

- Source: Terminal session screenshots, log file renders
- Acquisition: Automated screenshot pipeline (monospace-only, no prose context)
- Labels required: `code_confidence=1.0`, `capture_method=camera_smartphone` or
  `born_digital`, `color_mode=color`
- Status: ✅ 20 `terminal_pil_render` images registered | ⏳ Additional terminal screenshots pending

---

### Phase 9: Mixed OOD (OOD-Mixed) — P1 (sub-sources 9a-1 and 9a-2 are P0)

**Target: 700 images total across 4 sub-groups** (script default: 762)

> **Synthetic coverage**: `scripts/generate_ood_mixed.py` (Recipe 13) — 762 images. Reads all
> entries in `ood_registry.jsonl` with 1–2 existing OOD categories, selects those whose source
> files exist on disk, and applies one additional augmentation to push to ≥3 OOD dimensions.
> Four augmentation strategies: `add_geometry` (perspective warp → adds `ood_geometry`),
> `add_degradation` (JPEG + contrast → adds `ood_degradation`), `add_resolution`
> (downsample–upsample cycle → adds `ood_resolution`), `add_shadow` (radial vignette →
> adds `ood_degradation`). Inherits all ground-truth fields from the source registry entry and
> merges augmentation-specific labels. **Must be run LAST** after all other Phase 3 scripts
> have populated the registry (≥90% of their targets).
>
> **Specification:** The ideal OOD-Mixed set contains images that stress-test *multiple heads
> simultaneously*, with particular emphasis on *cascade failure scenarios* in the two-model
> pipeline (MobileNetV4 → SigLIP 2). Each sub-source specifies exactly which heads are stressed,
> which cascade failure is tested, and what the ideal evaluation outcome is. Unlike
> single-category OOD images, OOD-Mixed images carry labels for ALL applicable heads and include
> the `evaluation_pipeline_stage` tag to distinguish cascade tests from single-stage tests.
>
> The `ood_categories` array on each image references all applicable OOD categories (e.g.,
> `["ood_geometry", "ood_script"]` for Mongolian TTB + extreme perspective).

### Cascade Failure Scenarios

The following cascade failure scenarios are identified by the 2026-02-23 corpus review as
critical gaps in the current OOD-Mixed sub-source coverage. These scenarios are not yet
fully covered by 9a-1 through 9d-3 and require dedicated test image acquisition.

#### MNV4-H3 → SigLIP G5-5 Resolution Cascade

- **Scenario**: Vector PDF rendered at 72 DPI; large fonts appear low-res at the pixel level
- **Risk**: MNV4-H3 incorrectly flags the document for upscaling; SigLIP receives distorted
  input after unnecessary bicubic interpolation corrupts fine text features
- **Test images needed**: 100 vector PDFs (born-digital) rendered at 72/100/150 DPI
- **Expected behavior**: Model should NOT upscale large-font low-DPI vector docs — character
  height at 72 DPI from a 24pt font is sufficient; upscaling would waste compute and introduce
  interpolation artifacts
- **Heads stressed**: MNV4-H3 (resolution_quality_reg), SIG-G5-5 (resolution_quality_reg)
- **Status**: ❌ Not yet acquired — add as OOD-Mixed sub-source 9e-1 (P1)

#### Clean-But-Novel False Positive Rate

- **Scenario**: Pristine documents from domains never seen in training (novel government form
  templates, religious texts with unfamiliar layouts, unprecedented table structures)
- **Risk**: Novel-domain documents triggering spurious quality flags or erroneous geometric
  corrections due to unfamiliar visual patterns
- **Test images**: 200 images from novel source domains (government forms, religious texts)
- **Expected behavior**: Quality heads should output near-1.0 (high quality); classification
  heads (script, capture) should produce correct predictions; orientation/skew heads should
  NOT apply correction to correctly-oriented clean documents
- **Heads stressed**: All 22 heads (false positive rate measurement)
- **Status**: ❌ Not yet acquired — add as OOD-Mixed sub-source 9e-2 (P1)

---

#### 9a — MobileNetV4 Cascade Failures — target: 200 images

**What is tested**: Inputs where MobileNetV4 Stage 1 either produces an ambiguous output or
an incorrect output that degrades the corrected image passed to SigLIP 2 Stage 2.

**`evaluation_pipeline_stage`**: `["mobilenetv4", "siglip2"]` for all sub-sources in 9a.

##### 9a-1. Symmetric document ambiguity — target: 100 images [P0]

> **Re-prioritized to P0 per corpus review 2026-02-21**: cascade failures are the
> highest-risk production mode. Must be validated before any deployment. Images can be derived
> from existing labeled orientation data with zero additional acquisition cost.

- **OOD dimension**: Documents with no reliable orientation cue — blank pages, symmetric content,
  figure-only pages, pages with very sparse non-directional text
- **Cascade tested**: MNV4-H1 produces low-confidence output; if rotation is applied, SigLIP 2
  G3-1 receives a randomly rotated "corrected" image; both orientation heads should abstain rather
  than apply a correction that may be wrong
- **Performance targets**:
  - MNV4-H1: confidence < 0.9 on ≥ 80% of images (trigger abstention threshold); apply no
    rotation on ≥ 85% of images (abstention rate ≥ 85%)
  - SIG-G3-1: confidence < 0.9 on ≥ 80% of images
  - Failure: either model applies rotation with > 90% confidence on a symmetric document
- **Label requirements**: `orientation` (human-verified), `orientation_ambiguous=True`,
  `capture_method`, IQA labels
- **`ood_categories`**: `["ood_geometry", "ood_mixed"]`
- **Sources**: Wikipedia article screenshot pages, government blank forms, mathematical
  diagrams without text, figure-only document pages — NOT from DocLayNet without dedup
- **Exclusion**: Images where a careful human can determine the correct orientation with
  > 90% confidence (those belong in OOD-Geometry, not here)

##### 9a-2. Camera perspective tilt >30° — target: 100 images [P0]

> **Re-prioritized to P0 per corpus review 2026-02-21**: cascade failures are the
> highest-risk production mode. Must be validated before any deployment. Images can be derived
> from existing labeled skew data with zero additional acquisition cost.

- **OOD dimension**: Extreme perspective distortion making skew measurement unreliable and
  warping severity ambiguous
- **Cascade tested**: MNV4-H2 skew regression produces inaccurate angle; `conf ≥ 0.7` filter
  should reject; SIG-G5-3 warping regression conflates perspective with page warping
- **Performance targets**:
  - MNV4-H2: confidence < 0.7 (triggering abstention) on ≥ 70% of images with > 30° tilt
  - SIG-G5-3: abstain (return confidence < 0.5) or produce MAE < 0.3 relative to true
    warping severity excluding the perspective component
  - Failure: MNV4-H2 predicts skew with > 0.7 confidence on > 30° tilt images (conf gate broken)
- **Label requirements**: `skew_angle_degrees` (measured from control points), `orientation`,
  `warping_severity` (perspective only), `warping_type=perspective`,
  `capture_method=camera_smartphone`
- **`ood_categories`**: `["ood_geometry", "ood_capture", "ood_mixed"]`
- **Sources**: Internal photography — physically tilt documents at 30–60° on 3 axes before
  photographing; include rotation ambiguity (some tilted docs also appear rotated)

---

#### 9b — IQA Compound Degradation Cascades — target: 200 images

**What is tested**: Compound degradation scenarios that simultaneously stress IQA heads and
page attribute heads, with some specifically testing cross-model cascade behavior.

##### 9b-1. ≥5 simultaneous distortions + book gutter — target: 80 images

- **OOD dimension**: Compound degradation stack (blur + noise + contrast + skew + compression)
  combined with asymmetric book gutter shadow gradient (sd7k is flat-only, so gutter = OOD)
- **Heads stressed**: ALL SIG-G1 IQA heads (G1-1 iqa_overall, G1-2 iqa_sharpness, G1-3 iqa_color_fidelity), SIG-G5-2 (shadow_reg), SIG-G5-3 (warping_reg)
- **Critical requirement**: Must use a *different* augmentation engine from training Augraphy
  pipeline. This is mandatory — images assembled from the same Augraphy pipeline used in IQA
  training will not measure OOD generalization.
- **Performance targets**:
  - SIG-G1-1 (iqa_overall): VQualA ≥ 0.60 (floor) on these compound cases
  - SIG-G5-2 (shadow_reg): MAE < 0.25 (harder than flat-shadow IQA training data)
- **Label requirements**: 3-dim DIQA scores (`iqa_overall`, `iqa_sharpness`, `iqa_color_fidelity`),
  `shadow_severity`, `shadow_type=book_gutter`, `warping_type` (combination), `color_mode`, `document_age`
- **`ood_categories`**: `["ood_degradation", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["siglip2"]`

##### 9b-2. Screen recapture moiré + orientation ambiguity — target: 60 images

- **OOD dimension**: Screen recapture (moiré/RGB banding) combined with document orientation
  near 45° (diagonal) making both capture classification and orientation detection ambiguous
- **Cascade tested**: MNV4-H1 cannot determine if diagonal content is 45° skew or 45°-rotated
  document; screen recapture artifacts degrade all IQA signals
- **Heads stressed**: MNV4-H1, MNV4-H2, SIG-G1-1 through G1-6, SIG-G5-1 (capture_cls)
- **Performance targets**:
  - MNV4-H1: confidence < 0.9 on ≥ 60% of diagonal images (abstention expected)
  - SIG-G5-1: correctly classify as `camera_smartphone` or related capture class ≥ 70%
- **Label requirements**: All IQA scores, `capture_method=camera_smartphone`,
  `orientation` (human-verified), `skew_angle_degrees`, `color_mode=color`
- **`ood_categories`**: `["ood_capture", "ood_degradation", "ood_geometry", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["mobilenetv4", "siglip2"]`

##### 9b-3. Aged paper + fax halftone + bleed-through — target: 60 images

- **OOD dimension**: Historical document degradation (yellowing + foxing) combined with fax
  halftone screening and visible reverse-side bleed-through — compound degradation not
  represented in IQA training data
- **Heads stressed**: ALL SIG-G1 IQA heads, particularly G1-1 (iqa_overall)
- **Performance targets**:
  - SIG-G1-1 (iqa_overall): VQualA ≥ 0.60 (floor); correctly assign POOR or ILLEGIBLE quality rating
  - SIG-G1-2 (iqa_sharpness): must not over-penalize halftone screening as motion blur
- **Label requirements**: 3-dim DIQA scores (`iqa_overall`, `iqa_sharpness`, `iqa_color_fidelity`),
  `document_age=historical`, `color_mode`, `capture_method` (likely fax or scanner_flatbed)
- **`ood_categories`**: `["ood_degradation", "ood_domain", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["siglip2"]`

---

#### 9c — Script × Degradation Interactions — target: 150 images

**What is tested**: Script and degradation combinations that test joint generalization — whether
the model correctly identifies scripts even under severe degradation, and whether the degradation
signal is calibrated per-script.

##### 9c-1. Mongolian TTB + aged + extreme perspective — target: 60 images

- **OOD dimension**: Mongolian (permanently reserved script) + aged document degradation +
  camera perspective distortion. All three are OOD simultaneously.
- **Open-set requirement**: SIG-G2-1 must trigger open-set rejection via Energy Score +
  temperature scaling (calibrated post-training), with no in-training class assigned > 50%
  confidence, despite degradation making the script harder to read. If the model wrongly
  identifies it as another script with high confidence, that is a double failure.
- **Heads stressed**: SIG-G2-1 (open-set), MNV4-H2, SIG-G5-3, SIG-G1-1 (iqa_overall)
- **Performance targets**:
  - SIG-G2-1: Energy Score rejection on ≥ 80% of Mongolian images; no single class > 50% confidence
  - Failure: model assigns > 50% confidence to any in-training script class
- **Label requirements**: `script=Mong`, `open_set=true`, `text_direction=ttb`,
  `document_age=aged`, `warping_severity` (perspective)
- **`ood_categories`**: `["ood_script", "ood_geometry", "ood_degradation", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["mobilenetv4", "siglip2"]`

##### 9c-2. Arabic RTL binarized + extreme JPEG — target: 50 images

- **OOD dimension**: Arabic RTL script (in training but uncommon) with binarized color mode
  (eliminates shadow measurement) and extreme JPEG compression (quality < 40)
- **Heads stressed**: SIG-G2-1 (must still identify Arabic despite binarization + JPEG),
  SIG-G1-1 (iqa_overall), SIG-G1-2 (iqa_sharpness), SIG-G5-2 (`shadow_unmeasurable` flag expected)
- **Performance targets**:
  - SIG-G2-1: ≥ 75% accuracy on Arabic despite binarization + JPEG
  - SIG-G5-2: must flag `shadow_unmeasurable=True` (not produce invalid severity estimate)
  - SIG-G1-1: iqa_overall should reflect severe degradation from binarization + JPEG
- **Label requirements**: `script=Arab`, `text_direction=rtl`, `color_mode=binarized`,
  3-dim DIQA scores (DeQA-Doc pseudo-labeled), `shadow_unmeasurable=True`
- **`ood_categories`**: `["ood_script", "ood_degradation", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["siglip2"]`

##### 9c-3. Historical multi-script manuscript — target: 40 images

- **OOD dimension**: Medieval or Ottoman bilingual documents with both Latin and Arabic scripts
  on the same page — script detection must handle MIXED class accurately; the visual style of
  historical manuscripts is outside the synth-v3 training distribution
- **Heads stressed**: SIG-G2-1 (MIXED class), SIG-G4-1 (handwriting presence — likely DOMINANT),
  SIG-G1-1 (iqa_overall — historical paper degradation)
- **Performance targets**:
  - SIG-G2-1: correctly identify as MIXED on ≥ 60% of bilingual pages
  - SIG-G4-1: correctly classify handwriting presence (likely SUBSTANTIAL or DOMINANT)
- **Label requirements**: `script=MIXED`, `text_direction` (if determinable), `document_age=historical`,
  `handwriting_presence` (for manuscripts with clear script writing), all 3 DIQA IQA scores (`iqa_overall`, `iqa_sharpness`, `iqa_color`)
- **`ood_categories`**: `["ood_script", "ood_domain", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["siglip2"]`
- **Sources**: Public domain Ottoman archives, medieval manuscripts from Wikimedia Commons,
  Library of Congress, Open Access British Library manuscripts

---

#### 9d — Handwriting × Script × Quality Interactions — target: 150 images

**What is tested**: Scenarios where handwriting detection, script detection, and quality
assessment interact — the model must jointly reason about all three.

##### 9d-1. ILLEGIBLE Arabic cursive + low-quality scan — target: 60 images

- **OOD dimension**: Arabic cursive handwriting (KHATT — may be in training but ILLEGIBLE class
  is a void in current training) combined with low-quality scan artifacts (blur + low contrast)
- **Cascade tested**: If IQA quality is poor enough, does the model correctly classify
  handwriting presence AND script AND report ILLEGIBLE legibility — or does degradation mask
  the handwriting signal entirely?
- **Heads stressed**: SIG-G4-1 (presence — should be SUBSTANTIAL), SIG-G4-2 (legibility —
  should be ILLEGIBLE), SIG-G2-1 (script — should be Arab), SIG-G1-1 (iqa_overall — should be POOR)
- **Performance targets**:
  - SIG-G4-1: SUBSTANTIAL or DOMINANT on ≥ 75% of these images
  - SIG-G4-2: ILLEGIBLE or POOR on ≥ 60% of these images
  - SIG-G2-1: Arab on ≥ 70% of these images despite degradation
  - Failure: model reports NONE handwriting presence because blur obscures handwriting signal
- **Label requirements**: All 5 G4 fields, `script=Arab`, all 3 DIQA IQA scores (`iqa_overall`, `iqa_sharpness`, `iqa_color`),
  `capture_method=scanner_flatbed` or `camera_smartphone`
- **`ood_categories`**: `["ood_handwriting", "ood_script", "ood_degradation", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["siglip2"]`
- **Dedup note**: KHATT pages selected from test split not used in training; run
  pHash dedup against any Arabic training data

##### 9d-2. CJK handwriting + book gutter shadow — target: 50 images

- **OOD dimension**: Full-page CJK handwriting (CASIA-HWDB — P0 prerequisite may not be in
  training yet) combined with book gutter shadow gradient (absent from sd7k flat training)
- **Heads stressed**: SIG-G4-1 (presence — DOMINANT), SIG-G4-3 (content type — should be prose
  or alphanumeric for CJK practice pages), SIG-G5-2 (shadow — book gutter is OOD)
- **Performance targets**:
  - SIG-G4-1: DOMINANT or SUBSTANTIAL on ≥ 70% of images
  - SIG-G5-2: MAE < 0.25 (gutter shadow harder than flat shadow training)
  - SIG-G2-1: Hans or Jpan on ≥ 70% of images
- **Label requirements**: All 5 G4 fields, `script=Hans` or `Jpan`, `shadow_severity`,
  `shadow_type=book_gutter`, IQA scores
- **`ood_categories`**: `["ood_handwriting", "ood_script", "ood_degradation", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["siglip2"]`

##### 9d-3. Form fill-in (printed + handwritten) + skew — target: 40 images

- **OOD dimension**: Printed form template with handwritten fill-in values, combined with
  physical camera skew (document held at angle). Tests the interaction of mixed
  printed+handwritten content with geometric correction requirements.
- **Cascade tested**: MNV4-H2 must correctly measure skew even though part of the document
  is handwritten; handwriting detection must classify SPARSE or MODERATE (form fill-in) not NONE
- **Heads stressed**: MNV4-H2 (skew — ensure printed form layout not confused by HW regions),
  SIG-G4-1 (presence — SPARSE for typical form fill-in), SIG-G4-4 (presence_reg — partial fill),
  SIG-G5-1 (capture_cls — camera)
- **Performance targets**:
  - MNV4-H2: MAE < 1.0° despite mixed content
  - SIG-G4-1: SPARSE or MODERATE on ≥ 70% of form images (not NONE)
  - SIG-G5-1: correctly classify capture method ≥ 75%
- **Label requirements**: `skew_angle_degrees` (measured), all 5 G4 fields,
  `capture_method=camera_smartphone`, IQA scores, `layout_type=form`
- **`ood_categories`**: `["ood_handwriting", "ood_geometry", "ood_mixed"]`
- **`evaluation_pipeline_stage`**: `["mobilenetv4", "siglip2"]`
- **Sources**: Public domain tax forms, insurance claim forms (blank versions only — no PII);
  or synthetically generated form templates with handwritten annotations added via IAM-style script

---

#### 9e — Cascade Failure Scenarios (P1, 300 images total)

**9e-1 — MNV4-H3 → SIG-G5-5 Resolution Cascade** — 100 images [P1]

- **Scenario**: Vector PDF at 72/100/150 DPI; large fonts appear low-resolution at pixel level
  but are perceptually adequate (24pt font at 72 DPI = ~32px char height, which is acceptable)
- **Risk**: MNV4-H3 incorrectly flags for upscaling → SIG-G5-5 receives distorted image
- **Expected behavior**: Model must NOT flag vector PDFs for upscaling regardless of stated DPI
- **Sources**: 35 DocLayNet born-digital PDFs (not in training split — dedup required), rendered
  at 72/100/150 DPI via PyMuPDF (100 images = 35 docs × 3 renders, approximately)
- **Labels**: `resolution_quality_score` (measured char height), `upscale_recommended = False`,
  `capture_method = born_digital`, `upscale_paradox = True`
- **Targets**: MNV4-H3 assigns score ≥ 0.5 at 72 DPI for 24pt+ fonts; failure threshold if
  MNV4-H3 scores < 0.4 on ≥20% of these images
- **Heads**: MNV4-H3, SIG-G5-5
- `ood_categories`: `["ood_resolution", "ood_mixed"]`
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]`

**9e-2 — Clean-But-Novel False Positive Rate** — 200 images [P1]

- **Scenario**: Pristine documents from novel domains (government forms, religious texts, thermal
  receipts) triggering spurious quality flags or geometric corrections
- **Risk**: Novel layout → erroneous deskew/CLAHE/correction applied; quality falsely flagged as poor
- **Expected behavior**: Quality score near 1.0; correct class predictions; no spurious corrections
- **Sources**: 200 images drawn from OOD-Domain Phase 7 (gov forms, religious texts, receipts),
  which may partially overlap with 7a–7c sub-sources (use as cross-category)
- **Labels**: All 22 heads labeled; expected values: high quality (>0.8), correct script, no
  shadow/warping, no spurious correction triggers
- **Target**: False positive rate < 10% on any head (spurious correction trigger or quality flag
  below 0.5 on a pristine document)
- **Heads**: All 22 (false positive rate evaluation)
- `ood_categories`: `["ood_domain", "ood_mixed"]`
- `evaluation_pipeline_stage`: `["mobilenetv4", "siglip2"]`

---

**Phase 9 Summary:**

| Sub-source | Count | Heads Stressed | Cascade |
|---|---|---|---|
| 9a-1. Symmetric document ambiguity | 100 | MNV4-H1, SIG-G3-1 | Yes |
| 9a-2. Camera perspective >30° | 100 | MNV4-H2, SIG-G5-3 | Yes |
| 9b-1. 5+ distortions + book gutter | 80 | All G1 + G5-2 + G5-3 | No |
| 9b-2. Screen recapture + orientation | 60 | MNV4-H1, MNV4-H2, All G1, G5-1 | Yes |
| 9b-3. Aged + fax + bleed-through | 60 | All G1 (especially G1-6) | No |
| 9c-1. Mongolian + aged + perspective | 60 | G2-1 (open-set), MNV4-H2, G5-3 | Yes |
| 9c-2. Arabic binarized + JPEG | 50 | G2-1, G1-5, G5-2 | No |
| 9c-3. Historical multi-script | 40 | G2-1, G4-1, G1-6 | No |
| 9d-1. ILLEGIBLE Arabic + low-quality | 60 | G4-1, G4-2, G2-1, G1-6 | No |
| 9d-2. CJK handwriting + gutter shadow | 50 | G4-1, G4-3, G5-2, G2-1 | No |
| 9d-3. Form fill-in + skew | 40 | MNV4-H2, G4-1, G4-4, G5-1 | Yes |
| 9e-1. Vector PDF resolution cascade | 100 | MNV4-H3, SIG-G5-5 | Yes |
| 9e-2. Clean-but-novel false positive | 200 | All 22 | No |
| **Total** | **1,000** | | |

---

## Per-Image Entry Template

Once images are acquired, add entries to `metadata_registry/ood_registry.jsonl` using the
full schema. See [OOD Dataset Design — Schema](../planning/OOD_DATASET_DESIGN.md#schema)
for the complete field reference.

Minimal required fields for every entry:

```json
{
  "sha256": "abc123...",
  "phash": "def456...",
  "phash_hamming_threshold": 5,
  "source_path": "/mnt/e/image_detection/ood/{category}/{filename}",
  "ood_categories": ["ood_script"],
  "reason": "Mongolian (Mong) TTB reserved script — never in training",
  "registered_date": "2026-02-21",
  "acquisition_method": "MTHv2 dataset download",
  "license": "Academic use only",
  "dedup_verified": true,
  "dedup_date": "2026-02-21",
  "evaluation_pipeline_stage": ["mobilenetv4", "siglip2"],
  "ground_truth": {
    "iqa_overall": null,
    "iqa_sharpness": null,
    "iqa_color_fidelity": null,
    "iqa_sample_weight": null,
    "script": "Mong",
    "open_set": true,
    "orientation": 0,
    "skew_angle_degrees": 0.0,
    "handwriting_presence": "NONE",
    "handwriting_presence_score": 0.0,
    "handwriting_legibility": "NOT_APPLICABLE",
    "handwriting_legibility_score": 0.0,
    "handwriting_content_type": "not_applicable",
    "capture_method": "scanner_flatbed",
    "shadow_severity": 0.0,
    "shadow_type": "none",
    "warping_severity": 0.0,
    "warping_type": "none",
    "watermark_severity": 0.0,
    "code_confidence": 0.0,
    "resolution_quality": null,
    "color_mode": "grayscale",
    "document_age": "modern",
    "text_direction": "ttb"
  },
  "open_set_evaluation": {
    "expected_behavior": "energy_score_rejection",
    "reject_threshold": 0.50,
    "rejection_method": "energy_score_temperature_scaling",
    "notes": "Model must not assign >50% confidence to any in-training script class. Energy Score threshold calibrated post-training — see Open-Set Rejection Protocol."
  }
}
```

---

## OOD Detection Infrastructure

The following OOD detection and evaluation infrastructure has been implemented on branch
`feat/ood-cross-model-agreement`:

- **OOD Detector**: `src/image_preprocessing_detector/detection/ood_detector.py` — Mahalanobis
  distance-based OOD detection in SigLIP 2 embedding space (AUROC 0.9963 on DIQA-5000 test vs
  synthetic OOD). See [CROSS_MODEL_AGREEMENT_SYSTEM.md](../planning/CROSS_MODEL_AGREEMENT_SYSTEM.md).
- **Cross-Model Validator**: `src/image_preprocessing_detector/detection/cross_model_validator.py`
  — Two-tier reliability detection (embedding distance + cross-model agreement scoring)
- **Cross-Model Calibration**: `src/image_preprocessing_detector/detection/cross_model_calibration.py`
  — Temperature scaling and calibration for cross-model agreement
- **OOD Evaluation Script**: `scripts/evaluate_ood_detection.py` — Evaluate OOD detection
  performance on the registered OOD corpus
- **OOD POC Dataset**: `scripts/generate_ood_poc_dataset.py` — Generate proof-of-concept OOD
  evaluation datasets
- **SigLIP 2 Embedding Extraction**: `scripts/extract_siglip2_embeddings.py` — Extract embeddings
  for Mahalanobis distance computation
- **DeQA-Doc Pseudo-Labeling**: `scripts/generate_diqa_pseudo_labels.py` + `scripts/gate_diqa_pseudo_labels.py`
  — OOD-gated pseudo-label pipeline. See [DEQA_DOC_PSEUDO_LABELING.md](../planning/DEQA_DOC_PSEUDO_LABELING.md).

### Registry Utilities

- **ood_utils.py** (`scripts/ood_utils.py`): `load_ood_registry(path)` → `(sha_set, phash_list)`;
  `append_registry_entry(entry, registry_path)`; `is_duplicate(sha256, phash, sha_set, phash_list)`
- **Domain enrichment**: `scripts/enrich_ood_domain.py` — all 9,170 records enriched with
  `enrichment.domain_level1`
- **CC-OCR harvest**: `scripts/harvest_ood_cc_ocr.py` — Hang(147), Cyrl(149), Arab(100), Jpan(50)
  ood_script + 100 ood_domain
- **Dataset builder**: `scripts/build_ood_dataset.py` — Assemble OOD evaluation sets from registry

### GT Schema Migration Note

The entry template in this catalog uses the target DIQA 3-dim schema (`iqa_overall`,
`iqa_sharpness`, `iqa_color_fidelity`, `iqa_sample_weight`). The current registry
(`ood_registry.jsonl`) still uses the legacy 6-head schema (`blur_score`, `noise_score`,
`contrast_score`, `compression_score`, `skew_score`, `overall_quality`). A schema migration
script is needed to:

1. Map legacy fields to DIQA dimensions via DeQA-Doc pseudo-labeling
2. Add `iqa_sample_weight` from OOD gating (Mahalanobis distance threshold)
3. Retain legacy fields as supplementary metadata during transition

---

## Notes

- All OOD images must be stored on E: drive under `/mnt/e/image_detection/ood/`
- Subdirectory per category: `ood_script/`, `ood_capture/`, `ood_degradation/`,
  `ood_handwriting/`, `ood_geometry/`, `ood_resolution/`, `ood_domain/`, `ood_code/`, `ood_mixed/`
- No OOD images may be uploaded to GCS training buckets
- Cross-category images are stored once in the primary category directory; `ood_categories`
  array references all applicable categories
- Acquisition progress updated monthly or after each acquisition phase
- After any new training dataset is added, re-run dedup protocol
  (see [Dedup Re-run Protocol](../planning/OOD_DATASET_DESIGN.md#dedup-re-run-protocol))

## Domain Enrichment Summary

All 9,170 registry entries have been enriched with `enrichment.domain_level1` labels.
See `OOD_COVERAGE_GAP_REPORT.md` for full breakdown.

| Domain | Count | % | Description |
|--------|-------|---|-------------|
| EDU | 2,724 | 29.7% | Educational / linguistic corpora, handwriting, scripts |
| UNK | 2,070 | 22.6% | DocSynth300K-derived (no category metadata), SD7K manga |
| GOV | 1,264 | 13.8% | Government forms, ID documents, tenders |
| TEC | 975 | 10.6% | Code screenshots, terminals, patents, manuals |
| SCI | 747 | 8.2% | arXiv papers, academic documents |
| FIN | 640 | 7.0% | Financial reports, corporate documents |
| SCN | 500 | 5.5% | Natural scene text (HierText street photos) |
| LGL | 235 | 2.6% | Laws, regulations (DocLayNet) |
| HIST | 15 | 0.2% | Historical documents |
| MED | 0 | 0.0% | Not yet acquired |
| REL | 0 | 0.0% | Not yet acquired |

## Script Coverage

| Script | ISO | Count | Notes |
|--------|-----|-------|-------|
| Hans (Simplified Chinese) | Hans | 300 | |
| Latin | Latn | 207 | Includes Fraktur subset |
| Cyrillic | Cyrl | 149 | Added via CC-OCR harvest |
| Hangul (Korean) | Hang | 147 | Added via CC-OCR harvest |
| Arabic | Arab | 106 | Includes Ottoman Arabic |
| Japanese | Jpan | 65 | |
| Malayalam | Mlym | 24 | |
| Gurmukhi (Punjabi) | Guru | 21 | |
| Kannada | Knda | 18 | |
| Thai | Thai | 12 | |
| Bengali | Beng | 11 | |
| Telugu | Telu | 9 | |
| Devanagari | Deva | 8 | |
| Oriya | Orya | 8 | |
| Tamil | Taml | 6 | |
| Armenian | Armn | 5 | Phase 2 preview script |
| Gothic | Goth | 5 | Historical script |
| Georgian | Geor | 5 | **Reserved script** — must remain OOD-only |
| Gujarati | Gujr | 4 | |

**Note on reserved scripts**: Georgian (Geor) now has 5 images in registry. Per the
[Script Reservation Policy](../planning/OOD_DATASET_DESIGN.md#script-reservation-policy),
Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) must NEVER appear in training manifests.
Mongolian and Syriac have 0 entries — acquisition still pending.
