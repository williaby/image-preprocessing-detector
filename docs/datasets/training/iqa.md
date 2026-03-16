---
l4_category: training-dataset
l4_dataset: iqa
l4_workstream: WS3
l4_source_datasets:
  - diqa-5000
  - ohr-bench
  - synth-multiscript-v3
l4_generation_script: scripts/prepare_multitask_datasets.py
l4_image_count: 116000
l4_status: in_progress
---

# IQA Training Dataset

> **Quick Stats**: 116K target images | 6 IQA regression heads (G1-1 through G1-6) | Dual-phase
> label strategy (Phase 1: real curated, Phase 2: tier_0_exact from augmentation params)
>
> **Status**: 🔄 In Progress | **Overall HAR Status**: Mixed — G1-5 (65/100), G1-4 (54/100),
> G1-3 (49/100), G1-1 (45/100), G1-2 (37/100), G1-6 (37/100) | **P0 Gaps**: 13

---

## HAR Assessment (5-Model Consensus Review, 2026-02-21)

| Head | HAR Score | Grade |
|------|-----------|-------|
| G1-1 blur | 45/100 | Needs Work |
| G1-2 noise | 37/100 | Needs Work |
| G1-3 contrast | 49/100 | Needs Work |
| G1-4 skew_severity | 54/100 | Needs Work |
| G1-5 compression | 65/100 | Marginal |
| G1-6 overall_quality | 37/100 | Needs Work |

Average: ~47/100 | Phase 2 synthetic pipeline: NOT STARTED (0/100,000 images)

---

## Consolidated P0 Gap Registry

All 13 P0 blockers that must be resolved before Phase 2 training can begin, consolidated from the
six G1 HAR files. Ordered by head, then by impact within each head.

| Gap ID | Head | One-Line Issue | Acceptance Criterion | Blocking Dependency |
|--------|------|----------------|---------------------|---------------------|
| IQA-BLUR-G01 | G1-1 | Phase 2 synthetic pipeline not created (0/100K assembled) | 100K blur images assembled with tier_0_exact labels | `prepare_multitask_datasets.py iqa` sub-command must be implemented |
| IQA-BLUR-G02 | G1-1 | Motion blur entirely absent from Phase 2 plan | ≥30% of Phase 2 G1-1 samples use linear kernel motion blur | IQA-BLUR-G01 (pipeline must exist first) |
| IQA-NOISE-G01 | G1-2 | Classical noise detector zero-variance — blocks all Phase 1 G1-2 labeling | Targeted VLM noise pilot run; SRCC vs. known sigma ≥ 0.55 measured | GPU VM required for injected-sigma pilot |
| IQA-NOISE-G03 | G1-2 | Phase 2 noise pipeline not created (0/100K assembled) | 100K noise images assembled with tier_0_exact labels | `prepare_multitask_datasets.py iqa` sub-command |
| IQA-CONTRAST-G01 | G1-3 | Semantic definition of contrast_score not documented; all labeling invalid until resolved | Definition documented in L2 schema guide: text-background separation via Michelson contrast at Canny edges | Blocks all G1-3 labeling |
| IQA-CONTRAST-G02 | G1-3 | `iqa_classical.py` uses global histogram spread — wrong metric for text documents | `label_contrast_classical.py` (edge-aware Michelson) built and run on DIQA-5000/OHR-Bench/RealDAE | IQA-CONTRAST-G01 must be resolved first |
| IQA-CONTRAST-G03 | G1-3 | Phase 2 contrast pipeline not created (0/100K assembled) | 100K contrast images assembled; spatial illumination gradient augmentation included | IQA-CONTRAST-G01; `prepare_multitask_datasets.py iqa` |
| IQA-COMP-G01 | G1-5 | Phase 2 re-save pipeline not created (0/100K assembled) | 100K re-saved images at QF 10/20/40/60/80; manifests with `compression_score = 1.0 - (QF/100)` | `prepare_iqa_compression_dataset.py` not yet created |
| IQA-COMP-G03 | G1-5 | Score convention conflict between scaffold v1.0 and head spec (quality vs. severity inversion) | Severity convention (0=pristine, 1=severe) adopted throughout; assertion added to assembly script | Must resolve before any labeling runs |
| IQA-COMP-G04 | G1-5 | Multi-generation JPEG re-compress absent from training | ≥10K chained JPEG samples in Phase 2; labels from DCT estimate of final level | IQA-COMP-G01 (addon) |
| IQA-SKEW-G01 | G1-4 | Severity transfer function undefined; naive angle-to-severity mapping is perceptually invalid | 300–500 human MOS calibration images collected; DPI-normalized piecewise transfer function fit; SRCC ≥ 0.65 validated | Human annotation budget required |
| IQA-SKEW-G03 | G1-4 | Phase 2 skew pipeline not created (0/100K assembled) | 100K skew images assembled with validated transfer function labels | IQA-SKEW-G01 must be resolved first |
| IQA-OVERALL-G01 | G1-6 | VLM SRCC 0.53 (non-rotated) below 0.65 gate; blocks OHR-Bench labeling | VLM prompt v2.0 validated on 30–50 images; SRCC > 0.65 achieved | Prompt v2.0 must be developed and re-validated before bulk labeling |

---

## Section 1 — Identity

| Field | Value |
|-------|-------|
| **Dataset Name** | `iqa` |
| **Head(s) Fed** | SIG-G1-1 `blur_score`, SIG-G1-2 `noise_score`, SIG-G1-3 `contrast_score`, SIG-G1-4 `skew_score`, SIG-G1-5 `compression_score`, SIG-G1-6 `overall_quality` |
| **Model(s)** | SigLIP 2 NAFlex (Group 1 — Image Quality Assessment) |
| **Task Type** | Regression 0–1 continuous severity score (all 6 heads); Gaussian NLL output (mu, sigma_sq) per head |
| **Primary L2 Field(s)** | `ml_image_quality.blur_score`, `ml_image_quality.noise_score`, `ml_image_quality.contrast_score`, `ml_image_quality.skew_score`, `ml_image_quality.compression_score`, `ml_image_quality.overall_score` |
| **Training Phase** | Phase 1 warmup (IQA + Script jointly trained); Phase 2 IQA degradation pre-training |
| **Target Size** | 116,000 images (16K Phase 1 curated + 100K Phase 2 synthetic) |
| **Image Size** | Variable; SigLIP 2 NaFlex preserves aspect ratio up to 784 patches |
| **Storage Location** | `E:\image_detection\03_training_datasets\iqa\` (pending assembly) |
| **GCS Path** | `gs://image_detection_b/iqa_training/` (pending upload) |
| **Assembly Script** | `scripts/prepare_multitask_datasets.py iqa` (not yet implemented) |
| **HAR File(s)** | [har/sig-g1-blur-score.md](../../planning/har/sig-g1-blur-score.md), [har/sig-g1-noise-score.md](../../planning/har/sig-g1-noise-score.md), [har/sig-g1-contrast-score.md](../../planning/har/sig-g1-contrast-score.md), [har/sig-g1-skew-score.md](../../planning/har/sig-g1-skew-score.md), [har/sig-g1-compression-score.md](../../planning/har/sig-g1-compression-score.md), [har/sig-g1-overall-quality.md](../../planning/har/sig-g1-overall-quality.md) |
| **DDR Files** | [diversity_reports/iqa_curated_ddr.md](../diversity_reports/iqa_curated_ddr.md), [diversity_reports/iqa_synthetic_ddr.md](../diversity_reports/iqa_synthetic_ddr.md) |

### Phase Architecture

This dataset serves two fundamentally different training roles:

**Phase 1 — Curated Real Documents (16K target)**
Feeds all 6 G1 heads but is the PRIMARY source for G1-6 (`overall_quality`). Labels are sourced
from human MOS (DIQA-5000), native quality scores (OHR-Bench), and VLM scoring. Phase 1 provides
real-world domain transfer signal that Phase 2 synthetic cannot supply.

**Phase 2 — Synthetic Augmentation (100K target)**
Feeds G1-1 through G1-5 as the PRIMARY training source. Labels ARE the augmentation parameters —
blur sigma, noise sigma, CLAHE clip limit, JPEG quality factor, and a content-aware skew severity
function — recorded at generation time (tier_0_exact, confidence = 1.0). Phase 2 is NOT blocked by
VLM labeling delays. It should be prioritized to enable early G1 training.

**Convention**: All G1 scores are 0–1 floats where 1.0 = perfect quality (no degradation) and
0.0 = severe degradation (worst case). This is the INVERSE of degradation severity.

---

## Section 2 — Status

### Overall Assembly Status

| Metric | Value |
|--------|-------|
| **Phase 1 Assembly Status** | 🔄 In Progress — VLM labeling at 200/5,500 DIQA images (pilot) |
| **Phase 2 Assembly Status** | 📋 Planned — pipeline script not yet created |
| **Phase 1 Current Count** | 5,499 / 16,000 (DIQA-5000 human MOS only; OHR-Bench + RealDAE unpopulated) |
| **Phase 2 Current Count** | 0 / 100,000 |
| **Combined Current Count** | 5,499 / 116,000 (4.7%) |
| **Primary Phase 1 Blocker** | VLM prompt v2.0 not yet validated (SRCC 0.53 non-rotated, gate is > 0.65) |
| **Primary Phase 2 Blocker** | `prepare_multitask_datasets.py iqa` sub-command not implemented |
| **Estimated Unblock Effort** | Phase 2: 3–5 days (immediately actionable); Phase 1 full: 10–13 days |
| **Last HAR Updated** | 2026-02-23 |

### Per-Head HAR Scores

| Head ID | Head Name | HAR Score | Status | P0 Gaps | Primary Blocker |
|---------|-----------|-----------|--------|---------|-----------------|
| SIG-G1-5 | `compression_score` | 65/100 | ⚠️ Needs Work | 4 | Phase 2 pipeline not built; DCT labels not run |
| SIG-G1-4 | `skew_score` | 54/100 | ⚠️ Needs Work | 3 | Severity transfer function undefined |
| SIG-G1-3 | `contrast_score` | 49/100 | ⚠️ Needs Work | 3 | Semantic definition not documented; edge-aware metric not built |
| SIG-G1-1 | `blur_score` | 45/100 | ⚠️ Needs Work | 3 | Phase 2 pipeline not built; Laplacian labels not run |
| SIG-G1-2 | `noise_score` | 37/100 | ❌ Blocked | 3 | Classical detector zero-variance; VLM SRCC unmeasured for noise |
| SIG-G1-6 | `overall_quality` | 37/100 | ❌ Blocked | 3 | VLM SRCC 0.53 below 0.65 gate; OHR-Bench L2 not populated |

**Priority note**: Phase 2 is not blocked by any VLM labeling issue. Implementing the Phase 2
pipeline unblocks G1-1 through G1-5 immediately and should be the first action taken.

---

## Section 3 — Source Pool Analysis

> *Derived from all six G1 HAR Section 2 files.*

### Phase 1 — Curated Real Document Pool (16K Target)

Phase 1 images provide real-world domain transfer anchor for all 6 heads. The same image pool is
labeled independently per head using different labeling methods per head.

| Source Dataset | Total Images | Label Method | Key Fields | Usable (Today) | Status |
|----------------|-------------|--------------|------------|----------------|--------|
| DIQA-5000 | 5,499 | Human MOS (overall); VLM pilot (dimension-specific) | `ml_image_quality.overall_score` populated; blur/noise/contrast/compression NOT populated | 5,499 (overall_quality only) | ✅ MOS available; dimension labels pending |
| OHR-Bench | ~8,500 | Native quality 0–100 scores (overall); VLM for dimensions | `overall_score` not yet in L2; native scores available | 0 | ⚠️ L2 population pending |
| RealDAE | ~1,200 | Distortion-type derivation (overall); classical detectors | L2 fields not populated | 0 | ⚠️ Derivation logic not built |
| DocLayNet subset | ~2,000 | VLM-scored (used for contrast/overall supplements) | Not yet sourced | 0 | 📋 Planned (P1) |
| **Phase 1 total** | **~15,199** | — | — | **5,499** | **34% of target** |

**Per-head Phase 1 label strategy summary**:

| Head | Label Method | Classical Path | VLM Viability | Current Usable |
|------|-------------|----------------|---------------|----------------|
| G1-6 `overall_quality` | Human MOS (DIQA-5000); VLM for OHR-Bench | No deterministic fallback | SRCC 0.53 (non-rotated); blocked pending prompt v2.0 | 5,499 (DIQA MOS) |
| G1-5 `compression_score` | DCT QF estimator (deterministic, ~12 img/s CPU) | ✅ Fully viable (no VLM needed) | N/A | 0 (not yet run) |
| G1-1 `blur_score` | Laplacian variance (SRCC ~0.7 vs human) | ✅ Viable (SRCC ~0.7) | Not recommended | 0 (not yet run) |
| G1-3 `contrast_score` | Edge-aware Michelson contrast at Canny edges | ⚠️ Script not yet built | Not recommended | 0 (not yet run) |
| G1-2 `noise_score` | VLM only (classical zero-variance defect on DIQA) | ❌ Blocked (zero variance) | SRCC unmeasured for noise | 0 |
| G1-4 `skew_score` | VLM or human MOS calibration | ❌ No classical path | Rotation construct mismatch risk | 0 |

### Critical Per-Head Gaps (Phase 1 and Phase 2)

**G1-1 blur_score — Motion Blur Absence**

WARNING — CRITICAL GAP: Motion blur is the most common real-world blur type (camera shake,
subject motion) and is ENTIRELY ABSENT from both Phase 1 and the planned Phase 2
pipeline. The current dataset covers only Gaussian/defocus blur.

This is the single highest-risk gap across all IQA heads — motion blur is what
users actually encounter in the wild.

**G1-2 noise_score — Zero Variance Detector**

WARNING — DETECTOR FAILURE: Classical DIQA noise detectors have zero variance on this dataset
(all documents appear clean to the detector). This means:

- VLM SRCC for noise has not been measured
- Camera-origin noise patterns are absent from Phase 2 plans
- Must run VLM pilot specifically for noise before Phase 2 starts

**G1-4 skew_score — Construct Conflict with G3-2**

WARNING — CONSTRUCT CONFLICT WITH G3-2: G1-4 measures skew as a DEGRADATION SEVERITY (0–1 scale,
where 1.0 = perfect quality / no skew). G3-2 measures skew as a GEOMETRIC ANGLE (degrees).

DO NOT use G3-2 skew angle data as a proxy for G1-4 skew severity.
They are different constructs with different label schemas. Using angle data for
severity training would corrupt the G1-4 head.

**G1-6 overall_quality — VLM SRCC Decision Gate**

Current status: SRCC = 0.53 (non-rotated subset) — GATE NOT MET

- SRCC >= 0.65: Proceed with VLM labels at scale (2–5K images)
- SRCC 0.60–0.65: Use with warning; flag in label provenance metadata
- SRCC < 0.60: HALT VLM labeling; use Phase 2 synthetic tier_0_exact labels instead

Required action: Re-validate 30–50 images with prompt v2.0 (orientation-independent
scoring, finer granularity). If SRCC > 0.60, proceed. Currently blocked.

### Phase 2 — Synthetic Pipeline (100K Target)

WARNING: Phase 2 pipeline (100,000 synthetic images with tier_0_exact labels) is
ENTIRELY UNBUILT as of 2026-02-21. No code has been written for:

- Motion blur augmentation pipeline
- Camera noise pattern simulation
- Edge-aware contrast measurement
- Multi-generation JPEG re-save pipeline
- Compound distortion combination

Phase 2 derives images from `synth-multiscript-v3` (190,485 images on GCS at
`gs://image_detection_b/synth_multiscript_v3/`) with augmentation parameters as tier_0_exact labels.

**Base dataset composition**:

- Color modes: 60% color, 30% grayscale, 10% binarized
- Document age: 80% modern, 15% aged, 5% historical
- Scripts: 27 ISO 15924 scripts, 198 languages
- DPI tiers: 72/100/150/200/300/400/600 (7 tiers)
- Skew range: ±22°

**Per-head Phase 2 label derivation**:

| Head | Augmentation Source | Normalization Formula | Label Confidence | Pipeline Status |
|------|--------------------|-----------------------|------------------|-----------------|
| G1-1 `blur_score` | Gaussian blur sigma 0.5–8.0; motion blur linear kernel 0–20px | `1.0 - clamp(sigma / sigma_max, 0, 1)` | tier_0_exact = 1.0 | 📋 Planned (Gaussian only; motion blur is P0 gap) |
| G1-2 `noise_score` | Gaussian noise sigma 0–28; salt-and-pepper amount 0–0.05 | `1.0 - clamp(sigma / 30.0, 0, 1)` | tier_0_exact = 1.0 | 📋 Planned |
| G1-3 `contrast_score` | CLAHE clip limit; gamma adjustment; spatial illumination gradient | `clamp(1.0 - contrast_reduction_factor, 0, 1)` | tier_0_exact = 1.0 | 📋 Planned |
| G1-4 `skew_score` | Skew angle parameter; content-aware transfer function (DPI-normalized, document-type-aware) | Validated piecewise linear (NOT simple sin) | tier_0_exact = 1.0 (pending transfer function validation) | 📋 Planned (transfer function undefined — P0 gap) |
| G1-5 `compression_score` | JPEG re-save at QF 10/20/40/60/80 | `1.0 - (jpeg_quality / 100.0)` | tier_0_exact = 1.0 | 📋 Planned (re-save strategy confirmed by consensus) |
| G1-6 `overall_quality` | Weighted average of all 5 individual degradation params | `weighted_mean(blur, noise, contrast, skew, compression)` with calibrated weights | tier_0_exact = 1.0 (formula must be calibrated vs Phase 1 MOS) | 📋 Planned |

### Pool Summary

| Metric | Phase 1 | Phase 2 | Combined |
|--------|---------|---------|---------|
| **Target** | 16,000 | 100,000 | 116,000 |
| **Current usable** | 5,499 | 0 | 5,499 |
| **Gap** | 10,501 | 100,000 | 110,501 |
| **Real vs. synthetic ratio** | 100% real | 100% synthetic | ~14% real / ~86% synthetic |
| **Label quality ceiling** | tier_1_annotation (human MOS) / tier_1_classical | tier_0_exact (augmentation param) | — |

---

## Section 4 — Label Schema

> *The Phase 1 and Phase 2 schemas differ by design and are maintained separately.*

### Phase 1 Label Schema (Real Documents)

**Primary L2 Fields**: Per-head fields in `ml_image_quality.*`
**Type**: float
**Range**: 0.0–1.0 (1.0 = perfect quality, 0.0 = severe degradation)
**Provenance Tier**: tier_1_annotation (human MOS, DIQA-5000) or tier_2_model (DeQA-Doc pseudo-labels)

```json
{
  "image_path": "iqa/phase1/images/{filename}.jpg",
  "source_dataset": "diqa-5000",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_1_annotation",
  "label_confidence": 1.0,
  "overall_quality": 0.78,
  "blur_score": 0.85,
  "noise_score": 0.90,
  "contrast_score": 0.72,
  "skew_score": 0.95,
  "compression_score": 0.60,
  "capture_method": "scanner_flatbed"
}
```

**Per-head label conventions (Phase 1)**:

| Head | Label Source | Value Convention | Notes |
|------|-------------|------------------|-------|
| `overall_quality` | Human MOS normalized: `(MOS - 1) / 4` from DIQA 1–5 scale; `raw_score / 100` from OHR-Bench | 0.0 = unusable, 1.0 = pristine | Rotation does NOT reduce score (orientation-independent) |
| `blur_score` | Laplacian variance, normalized to 0–1 | 1.0 = sharp, 0.0 = maximum blur | Expected SRCC ~0.7 vs human blur perception |
| `noise_score` | VLM noise-specific scoring (after SRCC pilot validation) | 1.0 = clean, 0.0 = severe noise | Classical detector blocked (zero-variance on DIQA) |
| `contrast_score` | Edge-aware Michelson contrast at Canny edge locations | 1.0 = optimal separation, 0.0 = washed out | Defined as text-background separation, NOT global histogram |
| `skew_score` | VLM severity or human MOS calibration set | 1.0 = straight, 0.0 = severely skewed | NOT a monotonic mapping of angle; DPI-normalized transfer function required |
| `compression_score` | DCT QF estimator; PNG/lossless → 0.0 (exact) | 1.0 = pristine/lossless, 0.0 = severe JPEG | Derivation: `1.0 - (QF / 100.0)` |

**Binarized image conventions (Phase 1)**:

| Head | Convention for `color_mode = binarized` |
|------|----------------------------------------|
| `blur_score` | 1.0 — post-binarization optical blur is unassessable |
| `noise_score` | 1.0 — continuous noise absent; Option A: 1.0 with mask flag |
| `contrast_score` | 1.0 — maximum binary separation (clean binarization) |
| `compression_score` | 0.0 — 1-bit images cannot have JPEG artifacts |
| `skew_score` | Score normally — binary edges carry angular cues |
| `overall_quality` | Legibility-based score in [0.4, 1.0]; 1.0 = clean sharp binary |

### Phase 2 Label Schema (Synthetic)

**Primary Label Source**: Augmentation parameters recorded at generation time
**Type**: float
**Range**: 0.0–1.0
**Provenance Tier**: tier_0_exact (confidence = 1.0 by construction)

```json
{
  "image_path": "iqa/phase2/images/{filename}.jpg",
  "source_dataset": "synth-multiscript-v3",
  "split": "train",
  "split_type": "train",
  "label_provenance": "tier_0_exact",
  "label_confidence": 1.0,
  "blur_score": 0.72,
  "noise_score": 0.88,
  "contrast_score": 0.65,
  "skew_score": 0.90,
  "compression_score": 0.20,
  "overall_quality": 0.77,
  "augmentation_params": {
    "blur_sigma": 2.24,
    "blur_type": "gaussian",
    "noise_sigma": 3.6,
    "noise_type": "gaussian",
    "contrast_reduction_factor": 0.35,
    "skew_angle_degrees": 1.2,
    "jpeg_quality": 80
  },
  "capture_method": "born_digital",
  "color_mode": "color",
  "document_age": "modern",
  "resolution_dpi": 300
}
```

**Phase 2 normalization formulas (frozen constants, stored in assembly script)**:

| Head | Formula | sigma_max / scale |
|------|---------|-------------------|
| `blur_score` | `1.0 - clamp(sigma / sigma_max, 0, 1)` | sigma_max = 8.0 (Gaussian); linear kernel 20px |
| `noise_score` | `1.0 - clamp(noise_sigma / 30.0, 0, 1)` | max_sigma = 30.0 |
| `contrast_score` | `clamp(1.0 - contrast_reduction_factor, 0, 1)` | factor 0 → 1.0 score |
| `skew_score` | Validated DPI-normalized piecewise transfer function | NOT sin(angle) — see IQA-SKEW-G01 |
| `compression_score` | `1.0 - (jpeg_quality / 100.0)` | QF range 10–100 |
| `overall_quality` | `weighted_mean(blur, noise, contrast, skew, compression)` | Weights calibrated against Phase 1 MOS |

### Label Statistics (Post-Assembly Targets)

| Head | Phase 1 Target Mean | Phase 2 Target Distribution | Severity Buckets |
|------|--------------------|-----------------------------|------------------|
| `blur_score` | ~0.70 (real docs mostly acceptable) | Uniform across [0.0, 1.0] | none/mild/moderate/severe |
| `noise_score` | ~0.80 (DIQA clean-document dominant) | Uniform across [0.0, 1.0] | clean/mild/moderate/severe |
| `contrast_score` | ~0.70 | Uniform across [0.0, 1.0] | optimal/adequate/low/minimal |
| `skew_score` | ~0.85 (most real docs are near-straight) | ≥20% near-zero (abs(angle) < 0.5°) | straight/mild/moderate/severe |
| `compression_score` | ~0.70 (document workflows default QF 75–85) | 5 tiers at QF 10/20/40/60/80 | pristine/minimal/mild/moderate/heavy/severe |
| `overall_quality` | ~0.72 (DIQA MOS distribution) | Derived from weighted degradation params | low/medium/high/excellent |

---

## Section 5 — Composition and Splits

### Phase 1 Composition (16K Target)

| Source | Target Count | Label Method | Notes |
|--------|-------------|--------------|-------|
| DIQA-5000 | 5,499 | Human MOS (overall) + classical per-dimension | Already processed; dimension labels pending |
| OHR-Bench | ~8,500 | Native quality scores + VLM for dimension-specific | Native overall scores normalized 0–100→0–1 |
| RealDAE | ~1,200 | Distortion-type derivation (overall) | Before/after pairs with known distortion types |
| DocLayNet subset | ~2,000 | VLM-scored supplement (P1) | For contrast / overall diversity |
| **Phase 1 total** | **~15,199–17,199** | — | — |

**Quality bucket stratification (Phase 1)**:

| Quality Bucket | Score Range | Target % | Notes |
|----------------|-------------|----------|-------|
| Low | 0.0–0.4 | 20% | Severely degraded; critical for regression calibration |
| Medium-low | 0.4–0.6 | 25% | Impaired but usable |
| Medium-high | 0.6–0.8 | 30% | Acceptable quality range |
| High | 0.8–1.0 | 25% | Near-pristine; important anchor for upper end |

### Phase 2 Composition (100K Target)

Each head is covered by uniform severity distribution across the 0–1 range. Additionally, a
compound-degradation stratum is targeted (P1 gap in current design — see Section 10).

| Degradation Category | Target Count | Notes |
|---------------------|-------------|-------|
| Single-degradation (one head severely degraded) | 85,000 | Primary training signal; 5 heads × ~17K each |
| Compound degradation (≥2 degradations simultaneously) | 15,000 | P1 gap — not yet in pipeline design |
| **Phase 2 total** | **100,000** | |

**Phase 2 severity coverage per head**:

| Head | Severity Levels | Target per Level | Special Requirements |
|------|----------------|------------------|---------------------|
| `blur_score` | ≥4 levels (none/mild/moderate/severe) | ~6,250 each | ≥30% motion blur; Gaussian + motion types |
| `noise_score` | ≥4 levels (clean/mild/moderate/severe) | ~6,250 each | Gaussian + salt-and-pepper types |
| `contrast_score` | ≥4 levels | ~6,250 each | CLAHE + spatial gradient augmentation required |
| `skew_score` | ≥4 levels + ≥20% near-zero (abs(angle) < 0.5°) | ~5K near-zero + ~5K per severity | Validated transfer function required |
| `compression_score` | 5 explicit QF tiers (10/20/40/60/80) | 20,000 each | Re-save strategy (not Augraphy) |

### Split Strategy

| Split | Images (Phase 1) | Images (Phase 2) | Total | Percentage |
|-------|-----------------|-----------------|-------|------------|
| Train | 11,199 | 70,000 | 81,199 | 70% |
| Val | 2,400 | 15,000 | 17,400 | 15% |
| Test | 2,400 | 15,000 | 17,400 | 15% |
| **Total** | **15,999** | **100,000** | **115,999** | **100%** |

**Split Method**: Document-level for Phase 1 (no image from the same document in both train and
test); image-level for Phase 2 (independent augmentation views).

**Random Seed**: 42

**Leakage Prevention**: Source dataset test splits reserved for OOD evaluation (DIQA-5000 test
split, OHR-Bench test split). Global split registry via SHA256 to prevent cross-dataset train/test
leakage. Phase 2 synth-multiscript-v3 base images SHA256-deduped against the 90K geometric skew
dataset to prevent cross-task leakage.

---

## Section 6 — 14-Dimension Diversity

> **Full DDR Audits**: [iqa_curated_ddr.md](../diversity_reports/iqa_curated_ddr.md) (22.5/100),
> [iqa_synthetic_ddr.md](../diversity_reports/iqa_synthetic_ddr.md) (20.0/100)
>
> **Note on DDR scores**: Both DDR scores of 0.0/100 for the 14-dimension component reflect that
> the DDR tool loaded 0 samples (`samples_loaded=0`), not confirmed poor diversity. The
> synth-multiscript-v3 base has well-characterized diversity. Analyst estimates below are based on
> source composition analysis.
>
> **Overall Analyst Estimated Diversity**: ~55/100 (Phase 2 potential not yet realized)

Dimensions sorted by aggregate relevance across all 6 G1 heads:

| Dimension | L2 Field | Relevance | Target | Current (Analyst Est.) | Status |
|-----------|----------|-----------|--------|------------------------|--------|
| `capture_method` | `capture_method.method` | CRITICAL — camera blur/noise patterns differ fundamentally from scanner and born-digital; direct impact on G1-1 (motion blur absent), G1-2 (scanner banding vs. ISO grain), G1-3 (illumination gradients) | ≥20% camera, ≥30% scanner, ≥30% born-digital | Phase 1: DIQA mixed; Phase 2: all synthetic (no camera-origin) | ⚠️ 35/100 — camera entirely absent from Phase 2 |
| `degradation` | `quality.degradations` | CRITICAL — core training signal for all 5 degradation heads; must span full 0–1 range per dimension | ≥4 severity levels per dimension; ≥2 types per head (e.g., Gaussian + motion for blur) | Phase 1: real degradation variety, unknown distribution; Phase 2: designed to cover full range | ⚠️ 30/100 — Phase 2 single-type per head; compound absent |
| `color_mode` | `image_properties.color_mode` | HIGH — affects all 5 degradation heads differently: binarized eliminates optical blur/noise; grayscale vs. color affects noise visibility; contrast is maximum for 1-bit | ≥10% binarized, ≥30% grayscale | Phase 2 synth: 60% color / 30% grayscale / 10% binarized (strong) | ✅ 75/100 for Phase 2; ⚠️ unmeasured for Phase 1 |
| `document_age` | `image_properties.document_age` | HIGH — aged documents affect G1-1 (organic blur from paper degradation), G1-2 (foxing grain), G1-3 (ink fading + paper yellowing = primary contrast degradation pathway), G1-5 (archival compression) | ≥15% aged + historical | Phase 2 synth: 80% modern / 15% aged / 5% historical (good) | ✅ 70/100 for Phase 2; ⚠️ Phase 1 modern-dominant |
| `resolution_dpi` | `resolution.category` | HIGH — low DPI mimics blur (G1-1 disentanglement risk), affects noise-to-signal ratio (G1-2), DPI must be covariate in skew severity transfer function (G1-4) | ≥3 DPI tiers (low/standard/high) | Phase 2 synth: 7 DPI tiers (72/100/150/200/300/400/600) — strong; Phase 1: primarily 300 DPI | ✅ 70/100 for Phase 2 |
| `script_code` | `language.script_code` | MEDIUM — CJK fine strokes more diagnostic for blur/noise; Arabic stroke width patterns affect contrast measurement; script affects perceptibility of each degradation type | ≥3 script families | Phase 2 synth: 27 scripts, 198 languages (excellent); Phase 1: DIQA-5000 Latin-dominant | ✅ 80/100 for Phase 2; ⚠️ Phase 1 imbalanced |
| `domain` | `domain.level1` | MEDIUM — high-frequency content (tables, math, dense text) has more diagnostic signal for blur, noise, contrast; domain breadth required | ≥5 domains | DIQA-5000 + OHR-Bench: FIN, SCI, forms, general; synth-v3: diverse via script + source | ✅ 65/100 — adequate via source breadth |
| `layout_type` | `structure.layout_type` | LOW-MEDIUM — multi-column documents affect apparent contrast; narrow-ruled forms amplify perceived skew severity; image-heavy pages are less diagnostic for noise | ≥3 types | Phase 1: diverse sources; Phase 2: synth-v3 distribution | ⚠️ 40/100 — unmeasured |
| `handwriting` | `structure.has_handwriting` | LOW — handwriting presence is largely independent of IQA degradation severity for these heads | ≥2 classes | Phase 1 partial | ⚠️ 40/100 |

### Key Diversity Gaps

- **Camera-origin blur and noise entirely absent from Phase 2**: Phase 2 is entirely synthetic
  (born_digital equivalent). Motion blur and camera ISO grain — the most common real-world blur and
  noise sources for mobile-captured documents — have no representation in Phase 2 training data.
  This is the single most important gap for G1-1 and G1-2 production generalization.
- **Compound degradation stratum absent**: Phase 2 design applies one degradation type at a time
  per image. Real-world documents frequently exhibit multiple degradation types simultaneously
  (low-light camera: motion blur + high ISO noise). A 15% compound-degradation stratum (P1 gap)
  is required before evaluation begins.
- **Phase 1 L2 metadata not loaded into DDR tool**: All dimension scores show "Not measured"
  because assembled manifests have not been ingested. DDR 0.0/100 automated score reflects
  this metadata gap, not confirmed poor diversity.

---

## Section 7 — Wild Condition Coverage

> **HAR Section 5 References**: See individual HAR files for per-head wild condition coverage.
>
> **Overall Wild Condition Score (iqa-curated DDR)**: 8.3/100 (0 covered / 1 partial / 5 missing)
>
> **Overall Wild Condition Score (iqa-synthetic DDR)**: 0.0/100 (dataset not assembled)

The following wild conditions are the most critical across all G1 heads. A condition is "Covered"
only if labeled training examples exist or will exist in the assembled dataset.

| Wild Condition | Affected Heads | L2 Evidence | Status | Training Gap |
|----------------|---------------|-------------|--------|-------------|
| Multiply-distorted (≥5 simultaneous degradation types) | All G1 heads | `quality.degradations` | ❌ Missing from training | OOD-4a (500 images) evaluates this but training data contains no ≥5-simultaneous examples. Model must generalize from single-degradation training. P0 for OOD, P1 for training (compound stratum). |
| Motion blur (camera shake during document capture) | G1-1 `blur_score` | `quality.degradations` (blur subtype = motion) | ❌ Missing | Phase 2 plans Gaussian blur only. Linear kernel motion blur absent from augmentation plan. P0 gap. Camera-origin motion blur is the most common real-world blur type. |
| Scanner CCD banding (anisotropic structured horizontal noise) | G1-2 `noise_score` | `capture_method = scanner_flatbed` | ❌ Missing from Phase 2 | Phase 2 uses isotropic Gaussian/S&P noise only. Real scanner banding has directional frequency content completely absent from synthetic. |
| Aged/historical document degradation (yellowing, foxing, ink fading) | G1-2, G1-3, G1-6 | `image_properties.document_age` | ⚠️ Partial | Phase 2 synth: 20% aged/historical base; degradation profiles partially modeled. Phase 1 DIQA-5000 is modern-dominant. Foxing patterns not in augmentation stack. |
| Mobile phone motion blur + defocus combined | G1-1, G1-6 | `quality.blur_type` = motion AND defocus | ⚠️ Partial (DDR curated) | Only partial in iqa-curated DDR. Combined motion+defocus from low-light capture has different spectral profile than either alone. Not in Phase 2 plan. |
| JPEG compression mimicking blur / noise (QF ≤ 50) | G1-1, G1-2, G1-5 | `quality.degradations` | ⚠️ Partial | Phase 2 addresses compression independently. Label independence between G1-1/G1-2/G1-5 must be verified (Pearson r < 0.4 between labels) after assembly. |
| Binarized documents (special handling for each head) | All G1 heads | `image_properties.color_mode = binarized` | ⚠️ Partial | Phase 2 includes 10% binarized base images. Label conventions defined per head but not yet enforced in assembly pipeline. OOD-4d (100 images) tests this. |
| Spatial illumination gradient (uneven camera or scanner exposure) | G1-3 `contrast_score` | `capture_method = camera_smartphone` | ⚠️ Partial | Phase 1 real docs may contain some. Phase 2 requires spatial gradient simulation (confirmed P1 by G1-3 consensus). Pure CLAHE (global) is insufficient. |
| Screen recapture (RGB aliasing + moiré) | G1-2, G1-6 | `capture_method = screen_recapture` | ❌ Missing | Neither Phase 1 nor Phase 2 planned augmentations model screen recapture moiré. OOD-Capture 3a (200 images) evaluates this but no training analog exists. |
| Book gutter shadow + page curvature combined | G1-3, G1-6 | `physical_degradation.shadow_severity` + `warping_type` | ❌ Missing | Absent from all Phase 1 sources and Phase 2 augmentation design. OOD-4c (100 images) evaluates gutter shadow. |

---

## Section 8 — OOD Cross-Reference

> **Full OOD Catalog**: [OOD_DATASET_CATALOG.md](../OOD_DATASET_CATALOG.md)
>
> **HAR Section 6 Reference**: See individual G1 HAR files § Section 6.

| Field | Value |
|-------|-------|
| **Primary OOD Category** | OOD-Degradation (Phase 4, P0) |
| **OOD Target Images (all G1 heads)** | 800 images across 4 sub-sources |
| **OOD Acquisition Status** | ⏳ Not started (Phase 4) |

**OOD-Degradation Sub-sources**:

| OOD Sub-source | Images | Relevance to G1 | Stress Scenario | Label Method |
|----------------|-------:|-----------------|-----------------|-------------|
| 4a. Multiply-distorted (≥5 simultaneous types) | 500 | ✅ Direct — all G1 heads | Compound: gutter shadow + page curl + defocus blur + noise + JPEG. Each G1 head must score amid 4+ co-occurring degradations. | Human annotation required (classical detectors insufficient for compound distortion; zero-variance defect extends to OOD for G1-2) |
| 4b. Watermarked documents | 100 | ⚠️ Indirect — G1-3, G1-6 primarily | Watermark reduces effective text contrast; tests whether G1-3 correctly penalizes watermark-induced contrast reduction while G1-1/G1-2 scores remain near 1.0 | Human annotation or VLM (validated) |
| 4c. Book gutter shadow | 100 | ✅ Direct — G1-3, G1-6; ⚠️ Indirect — G1-1, G1-2 | Hard shadow gradient tests spatial contrast estimation; secondary effects on apparent blur/noise in shadow region | Human annotation |
| 4d. Binarized (1-bit) documents | 100 | ✅ Direct — all G1 heads (convention validation) | Tests label conventions: G1-1 blur ≈ 1.0, G1-2 noise ≈ 1.0, G1-3 contrast = 1.0, G1-5 compression = 0.0, G1-4 skew scored normally | Per-head convention enforcement |

**Cross-category OOD relevant to G1**:

| Category | Images | Relevant Heads | Notes |
|----------|-------:|----------------|-------|
| OOD-Capture 3c (4th-gen photocopies) | 150 | G1-2 noise | Best real-world noise stress test; iterative photocopy speckle |
| OOD-Capture 3a (screen recapture) | 200 | G1-2, G1-6 | Moiré patterns; no training analog |
| OOD-Mixed cascade | 500 | All G1 heads | Multi-distortion cascades including binarized + extreme JPEG and CJK + gutter shadow |

**Critical OOD labeling constraints**:

- G1-2 classical noise detector has zero-variance defect — OOD noise labels MUST use human
  annotation or validated VLM, not classical detector.
- G1-4 skew_score classical Hough detector invalid for compound/non-linear distortions — human
  annotation MANDATORY for OOD-4a skew labels.
- All 800 OOD-Degradation images ultimately require human annotation or validated VLM for
  compound distortion scenarios.

**OOD Leakage Risk**: DIQA-5000 and OHR-Bench are in Phase 1 training. All OOD sources must be
verified via SHA256 + pHash (Hamming ≤ 5) against all training manifests before registration.
OHR-Bench test split must be withheld from Phase 1 training for OOD evaluation.

---

## Section 9 — Assembly Pipeline

**Overall Status**: ❌ Phase 2 — pipeline not yet created (prioritize this first); 🔄 Phase 1 —
partially labeled (5,499 of 16,000)

### Phase 2 Assembly Commands (Prioritize First — NOT blocked by VLM)

```bash
# Phase 2: Build augmentation pipeline for G1-1 through G1-5
# Prerequisites: synth-multiscript-v3 accessible on GCS

# Dry run (validates without writing)
uv run python scripts/prepare_multitask_datasets.py iqa \
    --phase 2 \
    --source-gcs gs://image_detection_b/synth_multiscript_v3/ \
    --target-count 100000 \
    --heads blur noise contrast compression skew \
    --dry-run

# Full assembly (after dry-run validates)
uv run python scripts/prepare_multitask_datasets.py iqa \
    --phase 2 \
    --source-gcs gs://image_detection_b/synth_multiscript_v3/ \
    --target-count 100000 \
    --heads blur noise contrast compression skew

# Note: skew_score head requires validated transfer function before running
# Note: blur_score head requires motion blur augmentation type (P0 gap)
```

### Phase 1 Assembly Commands

```bash
# Prerequisites (run in order per head):

# G1-5 compression_score (fastest, no VLM needed)
uv run python scripts/label_compression_classical.py \
    --datasets diqa-5000 ohr-bench realdae \
    --output-field ml_image_quality.compression_score

# G1-1 blur_score (classical Laplacian, ~2 days)
uv run python scripts/label_blur_classical.py \
    --datasets diqa-5000 ohr-bench realdae \
    --output-field ml_image_quality.blur_score

# G1-3 contrast_score (requires edge-aware script, ~3 days to build)
uv run python scripts/label_contrast_classical.py \
    --datasets diqa-5000 ohr-bench realdae \
    --output-field ml_image_quality.contrast_score

# G1-6 overall_quality (OHR-Bench native scores — immediate)
uv run python scripts/populate_ohrb_quality.py \
    --normalize-range 0-100 \
    --output-field ml_image_quality.overall_score

# Full IQA Phase 1 assembly (after per-head labeling complete)
uv run python scripts/prepare_multitask_datasets.py iqa \
    --phase 1 \
    --dry-run

uv run python scripts/prepare_multitask_datasets.py iqa --phase 1
```

### Dependencies

| Dependency | Status | Required For |
|------------|--------|-------------|
| `prepare_multitask_datasets.py iqa` sub-command | ❌ Not created | Phase 1 + Phase 2 assembly |
| `label_blur_classical.py` | ❌ Not created | G1-1 Phase 1 Laplacian labels |
| `label_contrast_classical.py` (edge-aware Michelson) | ❌ Not created | G1-3 Phase 1 labels |
| `label_compression_classical.py` (DCT QF estimator) | ❌ Not created | G1-5 Phase 1 labels |
| `populate_ohrb_quality.py` (0-100 normalization) | ❌ Not created | G1-6 OHR-Bench scores |
| VLM prompt v2.0 (orientation-independent) | ❌ Not validated | G1-6 OHR-Bench VLM labeling |
| Skew severity transfer function (DPI-normalized) | ❌ Not defined | G1-4 Phase 2 labels |
| Motion blur augmentation generator | ❌ Not added to plan | G1-1 Phase 2 (P0 gap) |
| `synth-multiscript-v3` GCS access | ✅ Ready | Phase 2 base dataset |
| DIQA-5000 images + human MOS | ✅ Ready | G1-6 Phase 1 baseline |
| `diqa-5000_metadata.json` | ✅ Ready (5,499 records) | Phase 1 source |

### Generated Outputs

| File | Description |
|------|-------------|
| `iqa/train_manifest.json` | Flat JSON list of training records (both phases merged) |
| `iqa/val_manifest.json` | Flat JSON list of validation records |
| `iqa/test_manifest.json` | Flat JSON list of test records (held out for evaluation) |
| `iqa/phase1/images/` | Phase 1 curated images (or pointer to source dataset paths) |
| `iqa/phase2/images/` | Phase 2 synthetic augmented images |
| `iqa/augmentation_log.jsonl` | Per-image augmentation parameters for Phase 2 auditability |

---

## Section 10 — Gap Registry

> **Sources**: All six G1 HAR files § Section 8

### P0 Blockers (must resolve before assembly can run)

#### Phase 2 Pipeline Gaps (actionable immediately)

| Gap ID | Head(s) | Description | Root Cause | Remediation | Effort |
|--------|---------|-------------|------------|-------------|--------|
| IQA-BLUR-G01 | G1-1 | **Phase 2 synthetic pipeline not created.** 100K target, 0 assembled. Primary label source for blur_score. | `prepare_multitask_datasets.py iqa` not implemented | Implement `iqa --head blur_score` sub-command: select 100K from synth-v3, apply Gaussian blur (sigma 0.5–8.0), record sigma, normalize to score. | 3 days |
| IQA-BLUR-G02 | G1-1 | **Motion blur absent from Phase 2.** Gaussian-only training teaches filter statistics, not perceptual blur. Model will fail on camera-captured documents. Both consensus models: BLOCKED without motion blur. | Phase 2 plan specifies only Gaussian. | Add motion blur augmentation (linear kernel 0–20px, direction 0–180°). Target: ≥30% of Phase 2 samples. | 1 day (addon) |
| IQA-NOISE-G01 | G1-2 | **Classical noise detector zero-variance on DIQA-5000.** Blocks all Phase 1 labeling and OOD ground truth for G1-2. Wavelet MAD produces near-constant near-zero output on clean-document population — not a code bug. | DIQA-5000 is a clean-document benchmark; naturally low noise → no cross-image variance. | Run targeted VLM noise pilot (200 images with injected sigma at {0,3,6,10,15,20,25}); measure SRCC vs. known sigma. If SRCC ≥ 0.55, proceed with bulk VLM labeling. | 3–5 days |
| IQA-NOISE-G03 | G1-2 | **Phase 2 noise pipeline not created.** 100K, 0 built. | `prepare_multitask_datasets.py iqa` not implemented | Implement: apply `OneOf([GaussianNoise(sigma=u), SaltAndPepperNoise(amount=v)])` to synth-v3; record sigma as label; normalize. | 2–3 days |
| IQA-CONTRAST-G01 | G1-3 | **Semantic definition not documented.** `contrast_score` is ambiguous between global histogram spread (current `iqa_classical.py`) and text-background separation. All labeling is invalid until resolved. Consensus unanimous: use text-background separation. | No formal definition exists in L2 schema spec. | Document `contrast_score = text-background separation (local Michelson contrast at Canny edge locations)` in L2 schema guide and training design. Propagate to VLM prompt and Phase 2 augmentation spec. | 0.5 days |
| IQA-CONTRAST-G02 | G1-3 | **`iqa_classical.py` contrast metric is global histogram spread — insufficient.** Cannot achieve SRCC ≥ 0.65 with global metric on complex documents. | Classical detector built for Phase 1C using superseded global definition. | Build `label_contrast_classical.py` using edge-aware Michelson contrast at Canny edge locations. | 3 days |
| IQA-CONTRAST-G03 | G1-3 | **Phase 2 contrast pipeline not created.** 100K, 0 built. | `prepare_multitask_datasets.py iqa` not implemented | Implement: CLAHE clip + gamma + spatial illumination gradient augmentations (confirmed P0 by consensus — spatial gradient is required, not optional). | 3–5 days |
| IQA-COMP-G01 | G1-5 | **Phase 2 re-save pipeline not created.** 100K, 0 built. Re-save strategy confirmed superior to Augraphy (clean, unambiguous QF ground truth). | Pipeline script not created. | Create `scripts/prepare_iqa_compression_dataset.py`: load synth-v3 from GCS, re-save at QF 10/20/40/60/80, record `compression_score = 1.0 - (QF/100)`, write manifest. | 2–3 days |
| IQA-COMP-G03 | G1-5 | **Score convention conflict.** Scaffold v1.0 used quality convention (1=pristine was also labeled as severity=0); head spec uses severity convention (0=pristine). Must align before any labeling runs. | Inconsistency in original HAR scaffold, resolved in HAR v1.1. | Adopt severity convention (0=pristine, 1=severe artifacts) throughout; add assertion in assembly script. | 0.5 days |
| IQA-COMP-G04 | G1-5 | **Multi-generation JPEG absent from training.** Real documents are frequently re-compressed through email/print/scan workflows; 3rd-gen JPEG at QF=80 may be worse than 1st-gen QF=40. Consensus elevated to P0. | Phase 2 specifies single-pass re-save only. | Add chained JPEG augmentation to Phase 2 pipeline: re-save QF1 (80–90) → reload → re-save QF2 (40–60); label with DCT estimate of final level. Target: 10K chained samples. | 1 day (addon to IQA-COMP-G01) |
| IQA-SKEW-G01 | G1-4 | **Severity transfer function undefined.** Naive monotonic angle → severity mapping is perceptually INVALID and makes G1-4 redundant with SIG-G3-2 (skew_reg). Consensus unanimous: invalid. | No transfer function defined before this review. | (1) Collect 300–500 human MOS calibration images spanning multiple DPI tiers and document types; (2) fit DPI-normalized, document-type-aware piecewise transfer function; (3) validate SRCC ≥ 0.65. | 5–8 days |
| IQA-SKEW-G03 | G1-4 | **Phase 2 skew pipeline not created.** 100K, 0 built. Depends on IQA-SKEW-G01. | Not implemented. | Implement IQA sub-command with validated transfer function; include linear + perspective skew subtypes; SHA256 dedup against 90K geometric dataset. | 4–6 days |
| IQA-OVERALL-G01 | G1-6 | **VLM SRCC below 0.65 target.** Pilot: SRCC=0.39 (all images), 0.53 (non-rotated). Root cause: VLM penalizes rotation; 48% of highest-MOS DIQA images are rotated 90°. Blocks OHR-Bench labeling. | VLM prompt v1.0 conflates geometric orientation with perceptual quality. | Develop VLM prompt v2.0: orientation-independent scoring + scale anchoring with labeled examples. Validate on 30–50 DIQA images; gate: SRCC > 0.65. | 3–4 days |

#### Phase 1 Non-VLM Gaps (actionable independently)

| Gap ID | Head(s) | Description | Remediation | Effort |
|--------|---------|-------------|-------------|--------|
| IQA-BLUR-G03 | G1-1 | Phase 1 Laplacian labeling not run on DIQA-5000/OHR-Bench/RealDAE | Run `iqa_classical.py` Laplacian on all three datasets; normalize; write to L2 `ml_image_quality.blur_score` | 2 days |
| IQA-COMP-G02 | G1-5 | Phase 1 DCT labeling not run; field not populated | Run `iqa_classical.py` DCT QF estimator on DIQA-5000, OHR-Bench, RealDAE | 1–2 days |
| IQA-OVERALL-G02 | G1-6 | OHR-Bench overall_score not in L2 (native 0–100 scores available) | Normalize OHR-Bench native scores: `overall_score = raw_score / 100`; write to L2 metadata | 1–2 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Head(s) | Description | Remediation | Effort |
|--------|---------|-------------|-------------|--------|
| IQA-BLUR-G04 | G1-1 | Defocus blur (disk kernel) absent from Phase 2 | Add disk kernel (radius 1–10px) as third blur type; target ≥15% of Phase 2 samples | 0.5 days |
| IQA-BLUR-G06 | G1-1 | Binarized image blur convention not enforced in pipeline | Define and assert: binarized → `blur_score = 1.0`; add manifest flag | 0.5 days |
| IQA-NOISE-G04 | G1-2 | Noise-specific VLM SRCC not measured independently | Run targeted VLM pilot: 200 images with injected noise at known sigma; measure noise-specific SRCC | 1–2 days |
| IQA-NOISE-G05 | G1-2 | Scanner banding (anisotropic) absent from Phase 2 | Add horizontal banding simulation (additive noise with horizontal correlation length); target 15–20% of Phase 2 | 1 day |
| IQA-NOISE-G06 | G1-2 | Binarized image noise convention undefined | Define: `noise_score = 1.0` for binarized + manifest flag | 0.5 days |
| IQA-NOISE-G07 | G1-2 | Noise+blur compound condition absent | Add 10–15% compound noise+blur to Phase 2; record both parameters per image | 2 days |
| IQA-CONTRAST-G04 | G1-3 | Phase 2 augmentations limited to global CLAHE — spatial gradient not yet modeled | Extend Phase 2 stack: linear illumination gradient + radial vignetting + localized shadow patches | 2 days |
| IQA-CONTRAST-G05 | G1-3 | Phase 1 contrast field unpopulated for all datasets | Run `label_contrast_classical.py` on DIQA-5000, OHR-Bench, RealDAE; integrate into L2 | 2 days (after G02 script) |
| IQA-CONTRAST-G07 | G1-3 | Binarized document contrast convention not enforced | Define: `contrast_score = 1.0` for clean binarized; conditional label assignment | 0.5 days |
| IQA-COMP-G05 | G1-5 | Phase 1 JPEG quality distribution unknown — may be biased toward moderate QF | Run QF distribution analysis after DCT labeling; supplement low-QF samples if < 5% | 0.5 days |
| IQA-COMP-G07 | G1-5 | DCT SRCC vs DIQA-5000 MOS not yet measured | Compute SRCC after executing IQA-COMP-G02; target SRCC ≥ 0.60 | 0.5 days |
| IQA-SKEW-G02 | G1-4 | L2 `ml_image_quality.skew_score` unpopulated for all Phase 1 datasets | Run VLM labeling on Phase 1 using rotation-invariant skew severity prompt; validate on 200-image calibration set | 3–5 days |
| IQA-SKEW-G04 | G1-4 | VLM skew_score SRCC not independently measured (rotation construct mismatch risk) | Run targeted VLM validation; test rotated vs. non-rotated subsets separately | 2–3 days |
| IQA-SKEW-G05 | G1-4 | OOD-4a human annotation for skew_score not budgeted | Allocate human annotation budget for 500 OOD-4a images; establish IAA protocol | 3–4 days |
| IQA-SKEW-G06 | G1-4 | Page-curl and perspective skew subtypes absent from Phase 2 | Extend Phase 2 to include perspective warp (keystone) and page-curl paths | 3–4 days |
| IQA-OVERALL-G03 | G1-6 | Phase 2 Augraphy synthetic pipeline not created | Implement `prepare_multitask_datasets.py iqa` with Augraphy stack + ≥5-simultaneous compound option | 5–7 days |
| IQA-OVERALL-G05 | G1-6 | Phase 2 weighted-average aggregation formula not calibrated vs human MOS | After Phase 1 assembly, minimize (formula - MOS)² on DIQA-5000 calibration set; freeze weights | 2–3 days |

### P2 Nice-to-Have

| Gap ID | Head(s) | Description | Remediation |
|--------|---------|-------------|-------------|
| IQA-BLUR-G08 | G1-1 | Partial (spatially non-uniform) blur not representable | Add `blur_spatial_uniformity` field; source partial-blur examples |
| IQA-BLUR-G09 | G1-1 | Combined blur + noise compound not explicitly trained | Add compound augmentation; record both parameters; label independently |
| IQA-NOISE-G08 | G1-2 | Noise subtype labels not captured in Phase 2 manifest | Add `noise_subtype` field: gaussian/salt_pepper/scanner_banding/organic_grain |
| IQA-NOISE-G09 | G1-2 | Aged document foxing (organic grain) not in Phase 2 | Source historical document scans; add foxing simulation (orange-brown spot overlay) |
| IQA-CONTRAST-G08 | G1-3 | Contrast subtype labels not captured | Add `contrast_degradation_type` enum to Phase 2 manifest |
| IQA-CONTRAST-G10 | G1-3 | Colorful background documents underrepresented | Ensure Phase 2 colorful-background overlay augmentation generates ≥10% of Phase 2 |
| IQA-COMP-G09 | G1-5 | Mixed codec coverage (JPEG 2000 ringing vs JPEG blocking) | Document out-of-scope; extend in future phase |
| IQA-COMP-G10 | G1-5 | Near-lossless boundary testing (QF 95–100) absent from OOD | Add 25–50 near-lossless images to OOD-4a sampling |
| IQA-SKEW-G07 | G1-4 | Near-zero skew hairline coverage not validated | Stratify Phase 2 with ≥20% images at abs(angle) < 0.5°; apply label smoothing |
| IQA-SKEW-G08 | G1-4 | 90K bootstrap utilization strategy undefined | Document: 90K images as weak supervision (loss weight 0.1–0.2 for backbone warm-up only; zero weight on regression head) |
| IQA-OVERALL-G08 | G1-6 | VLM inter-rater reliability not measured | Run labeling on 100 images with two VLM configurations; compute agreement |
| IQA-OVERALL-G10 | G1-6 | Screen recapture wild condition permanently absent from training | Document as known OOD gap; monitor via OOD-Capture 3a (200 images) |

---

## Section 11 — Performance Targets

> **Source**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

All G1 heads are regression outputs. The SigLIP 2 architecture uses Gaussian NLL heads outputting
(mu, sigma_sq) per head, enabling uncertainty-aware inference.

| Head ID | Head Name | Task | Target Metric | Target Value | Test Set | Notes |
|---------|-----------|------|--------------|-------------|----------|-------|
| SIG-G1-1 | `blur_score` | Regression 0–1 | SRCC | ≥ 0.65 | OOD-Degradation (4a primary) | Vs. classical Laplacian ground truth or human blur annotations |
| SIG-G1-2 | `noise_score` | Regression 0–1 | SRCC | ≥ 0.65 | OOD-Degradation (4a primary), OOD-Capture 3c | Vs. classical noise estimation or human annotations |
| SIG-G1-3 | `contrast_score` | Regression 0–1 | SRCC | ≥ 0.65 | OOD-Degradation (4a, 4b, 4c, 4d) | Vs. classical histogram contrast or human annotations; definition = text-background separation |
| SIG-G1-4 | `skew_score` | Regression 0–1 | SRCC | ≥ 0.65 | OOD-Degradation (4a, 4d) | Vs. human MOS for skew severity; human annotation MANDATORY for OOD-4a (classical Hough invalid for compound) |
| SIG-G1-5 | `compression_score` | Regression 0–1 | SRCC | ≥ 0.65 | OOD-Degradation (all 4 sub-sources) | Vs. human MOS; DCT labels provide strong Phase 1 signal |
| SIG-G1-6 | `overall_quality` | Regression 0–1 | SRCC | ≥ 0.65 | OOD-Degradation (4a primary), DIQA-5000 held-out | Vs. human MOS on DIQA-5000 held-out set; final production target |

### Head-Level Sufficiency Gates

Before any G1 head can progress to model training, the following must be met:

| Gate | Applies To | Requirement |
|------|-----------|-------------|
| Phase 2 pipeline built | G1-1, G1-2, G1-3, G1-4, G1-5 | 100K synthetic images assembled with tier_0_exact labels |
| Label independence verified | All pairs | Pearson r < 0.4 between blur_score and compression_score labels; r < 0.5 between blur_score and noise_score labels at image level |
| Binarized conventions enforced | All G1 heads | Per-head policy documented and asserted in assembly script |
| Skew transfer function validated | G1-4 | SRCC ≥ 0.65 on 300–500 human MOS calibration set before full pipeline run |
| VLM SRCC gate | G1-2, G1-6 (OHR-Bench path) | SRCC > 0.65 (G1-6) or SRCC > 0.55 (G1-2) on 200-image noise pilot before bulk labeling |
| DDR re-run | All G1 heads | Load assembled manifests into DDR tool; validate 14-dim diversity automated scores |

### Achieved Results

| Head | Val SRCC | Test SRCC | Status |
|------|----------|-----------|--------|
| `blur_score` | — | — | ❌ Not trained (pipeline not built) |
| `noise_score` | — | — | ❌ Not trained (blocked) |
| `contrast_score` | — | — | ❌ Not trained (pipeline not built) |
| `skew_score` | — | — | ❌ Not trained (transfer function undefined) |
| `compression_score` | — | — | ❌ Not trained (pipeline not built) |
| `overall_quality` | — | — | ❌ Not trained (VLM SRCC below gate) |

---

## Related Documents

- **HAR Files**: [sig-g1-blur-score.md](../../planning/har/sig-g1-blur-score.md),
  [sig-g1-noise-score.md](../../planning/har/sig-g1-noise-score.md),
  [sig-g1-contrast-score.md](../../planning/har/sig-g1-contrast-score.md),
  [sig-g1-skew-score.md](../../planning/har/sig-g1-skew-score.md),
  [sig-g1-compression-score.md](../../planning/har/sig-g1-compression-score.md),
  [sig-g1-overall-quality.md](../../planning/har/sig-g1-overall-quality.md)
- **DDR Files**: [iqa_curated_ddr.md](../diversity_reports/iqa_curated_ddr.md),
  [iqa_synthetic_ddr.md](../diversity_reports/iqa_synthetic_ddr.md)
- **Head Spec**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)
- **Diversity Spec**: [DATASET_DIVERSITY_REQUIREMENTS.md](../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
- **Source Datasets**: [DATASET_QUICK_REFERENCE.md](../DATASET_QUICK_REFERENCE.md)
- **Skew Geometric Dataset** (bootstrap source for G1-4): [training/skew.md](skew.md)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-23 | Initial creation from HAR batch B review (6 G1 heads) |
