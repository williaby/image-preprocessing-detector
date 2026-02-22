# Diversity Remediation Plan

> **Generated**: 2026-02-21
> **Branch**: `feat/ood-dataset-diversity-framework`
> **Source**: Synthesized from 8 Dataset Diversity Reports (DDRs) + multi-model consensus reviews
> **DDR Location**: `docs/datasets/diversity_reports/`
> **Plan Scope**: 8 of 10 training datasets (shadow + warping blocked pending GPU labeling scripts)

---

## Executive Summary

All 8 evaluated datasets received an automated diversity score of 20.0–22.5/100, triggering the
"remediation required before training" threshold. The low scores are largely an artifact of
inaccessible manifest paths (Windows `E:/` drives and GCS `gs://` not mounted in WSL), which
prevents Section 2 (14-dimension diversity) from loading sample data. The wild condition coverage
matrix (Section 1) is fully informative and is the primary basis for prioritization.

**Cross-cutting root cause**: Curation strategies that optimize for measurability over
representativeness. Confidence filters, clean academic sources, and IID page sampling make
pipelines easier to operate but systematically exclude the training signal needed for production
robustness.

**Datasets cleared for training**: None — all 8 require at minimum one P0 remediation action.

**Earliest training-ready datasets** (after P0 remediation): orientation, skew, synth-multiscript-v3.

**Datasets requiring significant data acquisition before any training**: handwriting, capture-method.

---

## Dataset Readiness Overview

| Dataset | Wild Score | DDR Grade | Earliest Training | Blocking Issues |
| --- | --- | --- | --- | --- |
| orientation | 27.5/100 | Insufficient | After P0 metadata fix | Section 2 at 0.0 (no manifest access) |
| skew | 27.5/100 | Insufficient | After P0 angle rebalance | Confidence filter bias; domain shift |
| resolution-quality | 0.0/100 | Insufficient | After label redesign | char_height proxy invalid (r=0.18 MOS) |
| iqa-curated | 8.3/100 | Insufficient | After P0 compound augment | Missing joint degradation distribution |
| iqa-synthetic | 0.0/100 | Insufficient | After calibration study | Do NOT generate until calibration done |
| handwriting | 0.0/100 | Insufficient | 4–6 weeks (acquisition) | No data acquired; taxonomy undefined |
| capture-method | 0.0/100 | Insufficient | After 4-class redesign + sourcing | Only 1990s CCD scanners in RVL-CDIP |
| synth-multiscript-v3 | 12.5/100 | Insufficient | After Armn/Grek/Kore fixes | 8.6x class imbalance; 17 scripts below target |

---

## P0 Remediation Actions — Blocks Training

Actions that must complete before any training run can proceed for the affected dataset.

### P0-1: iqa-curated — Compound Augmentation Pipeline

**Dataset**: iqa-curated | **Effort**: 3–5 days | **Wild score after**: 8.3 → ~33

**Problem**: The 6-head SigLIP-G1 model must learn `P(blur, noise, contrast, skew_severity,
compression, overall_mos)` jointly. Training only on single-distortion images teaches an incorrect
mutually-exclusive prior, causing systematic under-prediction for all 6 heads under compound
degradation.

**Action**: Build a compound augmentation pipeline that applies random combinations of 2–5
distortion types (blur, noise, JPEG compression, contrast reduction, skew) to clean OHR-Bench
base images. Use applied parameters as per-head pseudo-labels. Derive `overall_mos` via a
heuristic penalty function (normalized sum of per-head severities). Target 5K–10K compound-
distorted examples.

**Dependencies**: Clean OHR-Bench base images (already available).

**Reference**: `docs/datasets/diversity_reports/iqa_curated_ddr.md` Section 7.4 Rec 1.

---

### P0-2: iqa-synthetic — Perceptual Calibration Study (CRITICAL GATE)

**Dataset**: iqa-synthetic | **Effort**: 4–6 days | **Wild score after**: 0 → ~100

**CRITICAL DECISION GATE**: Do NOT bulk-generate 100K images until this calibration study is
validated. Regenerating images costs only compute, but training on miscalibrated labels and
discovering the error post-training costs weeks of GPU time.

**Problem**: Simple parameter-to-label mapping (`blur_sigma=2.0` → `blur=0.6`) is resolution-
and content-dependent and non-linear. Pre-training on these tier_0 labels teaches spurious
correlations that degrade rather than improve performance vs. a random-init baseline when
fine-tuning on real human MOS labels.

**Action**:

1. Generate a calibration pilot set of ~500 images sampling different distortions and intensities
   across varied content types (text, images, low/high DPI)
2. Have 3+ team members provide MOS scores using ACR-HR protocol
3. Train a simple calibration model: `MOS = f(parameter, resolution, content_type)`
4. Only then bulk-generate 100K images using calibrated tier_1 labels

**Reference**: `docs/datasets/diversity_reports/iqa_synthetic_ddr.md` Section 7.4 Rec 2.

---

### P0-3: iqa-synthetic — Hybrid Causal Distortion Pipeline

**Dataset**: iqa-synthetic | **Effort**: 5–7 days | **Wild score after**: 0 → ~50

**Problem**: Random-order distortion application produces unrealistic artifact interactions.
Real camera pipelines apply degradations in a fixed order: optics → sensor → ISP → compression.
The model learns to recognize synthetic pipeline signatures rather than real-world degradations.

**Action**: Build hybrid Augraphy (physical realism) + custom causal pipeline (digital artifacts).
Use Augraphy for paper fiber, ink bleed, scanner lighting effects. Layer custom code for blur →
sensor noise → JPEG compression in causal order. Apply 2–5 random distortions stochastically
per image.

**Sequencing**: P0-2 must complete before P0-3. Generate calibration set first; pipeline
architecture informs the calibration study design.

**Reference**: `docs/datasets/diversity_reports/iqa_synthetic_ddr.md` Section 7.4 Rec 1.

---

### P0-4: handwriting — Define Annotation Taxonomy Before Any Acquisition

**Dataset**: handwriting | **Effort**: 3–5 days | **Wild score after**: Prerequisite unlock

**Problem**: Acquiring datasets without finalizing the label schema will result in inconsistent
training signal. `handwriting_density` is implicitly Latin-biased; CJK density norms differ
fundamentally. Without a script-aware annotation rubric, the head learns contradictory signal.

**Action** (must precede all dataset acquisition):

1. Expand `handwriting_script` taxonomy into 9 fine-grained classes:
   `Latin-Print`, `Latin-Cursive`, `CJK-Simplified`, `CJK-Traditional`,
   `Arabic-Naskh`, `Arabic-Ruqah`, `Arabic-Nastaliq`, `Devanagari`, `Cyrillic-Print`
2. Define `handwriting_density` as a 5-tier categorical annotation scheme mapping to float
   regression targets. `none` is the explicit base class — any handwriting increases complexity:

   | Tier | Float Range | Regression Target | Canonical Example |
   | --- | --- | --- | --- |
   | `none` | 0.0 | 0.0 | Fully printed page; zero handwriting |
   | `low` | 0.01–0.05 | 0.03 | Single signature or date on a form |
   | `medium` | 0.05–0.40 | 0.22 | Margin notes or partial field fill-in |
   | `high` | 0.40–0.75 | 0.575 | Substantially annotated; handwriting dominates |
   | `all` | 0.75–1.0 | 0.875 | Predominantly or fully handwritten page |

   Tier boundaries are defined as % of page area covered by handwriting, making them
   script-agnostic across Latin, CJK, Arabic, and other writing systems.

3. Finalize `content_type` 3-class definition to include hybrid (typed + handwritten) documents

**Reference**: `docs/datasets/diversity_reports/handwriting_ddr.md` Section 7.4 Rec 2.

---

### P0-5: handwriting — Multi-Script Dataset Acquisition

**Dataset**: handwriting | **Effort**: 4–6 weeks | **Wild score after**: 0 → ~60

**Problem**: All 5 non-Latin handwriting wild conditions are completely absent. The `handwriting_
script` head cannot learn any non-Latin script with 0 examples.

**Acquisition priority**:

| Priority | Dataset | Rationale | Where to Get |
| --- | --- | --- | --- |
| 1 | CASIA-HWDB (CJK) | Logographic; stress-tests all 5 heads; maximally different from Latin | NLPR CASIA database (request form) |
| 2 | KHATT (Arabic) | RTL cursive; critical for `handwriting_script` + `legibility` | khatt.ideas2serve.net (free academic) |
| 3 | FUNSD + Synthetic Forms | FUNSD 199 imgs critically insufficient; generate 5K+ synthetic forms | FUNSD + form template generation |
| 4 | IIIT-INDIC (Devanagari) | Shirorekha head line variation critical | IIIT Hyderabad research group |
| 4 | HKR (Cyrillic) | Complete Slavic script coverage | GitHub: abdoelsayed2016/HKR_Dataset |
| 5 | IAM (Latin) | Fill remaining Latin families — do NOT use as foundation | IAM online corpus |

**Minimum samples per class**: 2,000 images per fine-grained script class. Stratified allocation
reserves 24,000 of 60,000 budget for `handwriting_script`; remaining 36K for other heads.

**Reference**: `docs/datasets/diversity_reports/handwriting_ddr.md` Section 7.4 Rec 1.

---

### P0-6: capture-method — Simplify to 4-Class Head for v1

**Dataset**: capture-method | **Effort**: 1–2 days | **Wild score after**: Unblocks training

**Problem**: The 7-class head cannot be learned from 50K images at current coverage imbalance.
100% of scanner training data is 1990s CCD (RVL-CDIP); the `flatbed_cis` class is unlearnable.
50K ÷ 7 ≈ 7K/class is barely adequate even if balanced.

**Action**: Collapse 7 classes to 4 for v1 model:

- `scanned_flatbed` (merges `flatbed_cis` + `flatbed_ccd`)
- `scanned_adf` (new data required — see P1-7)
- `camera_capture` (merges `camera_smartphone` + `camera_professional`)
- `born_digital`

**v2 gate**: Expand back to 7 classes once ≥2K examples per fine-grained class are collected.

**Also required**: Add content verification (text layer check) to ingestion pipeline to prevent
born-digital PDFs wrapping scanned images from being mislabeled.

**Reference**: `docs/datasets/diversity_reports/capture_method_ddr.md` Section 7.4 Rec 1.

---

### P0-7: synth-multiscript-v3 — Script List Alignment Decision

**Dataset**: synth-multiscript-v3 | **Effort**: 1 sprint | **Wild score after**: Unblocks DDR rerun

**Problem**: Generated script list diverges from design spec:

- Unexpected: `Armn` (Armenian) + `Grek` (Greek) — not in original 27-script plan
- Missing: `Cher` (Cherokee) + `Cans` (Canadian Aboriginal Syllabics)
- Mislabeled: `Kore` for Korean — correct ISO 15924 code is `Hang`
- Mongolian: 0 images

**Required decisions (one sprint to resolve)**:

1. **Cher + Cans**: Add to generation plan (requires font acquisition — see Part 7B)
2. **Armn + Grek**: Formal decision — keep (expand to 29-script model) or remove before training
3. **Kore → Hang**: Trivial relabeling fix; do immediately

**Reference**: `docs/datasets/diversity_reports/synth_multiscript_v3_ddr.md` Section 7.

---

### P0-8: orientation — Re-run DDR with Manifest Ingestion Now Fixed

**Dataset**: orientation | **Effort**: 1 hour | **Wild score after**: Unblocks Section 2 scoring

**Problem**: Section 2 scores are 0.0/100 for all datasets because `_load_dataset_samples()`
previously skipped `E:/` and `gs://` paths. This is now fixed: `E:/` paths are converted to
`/mnt/e/` (WSL) and `gs://` paths are streamed via `gsutil cat`.

**Action**: Re-run the DDR generator for all datasets with accessible manifests:

```bash
python scripts/evaluate_dataset_diversity.py --dataset orientation --output docs/datasets/diversity_reports/
python scripts/evaluate_dataset_diversity.py --dataset skew --output docs/datasets/diversity_reports/
python scripts/evaluate_dataset_diversity.py --dataset resolution-quality --output docs/datasets/diversity_reports/
python scripts/evaluate_dataset_diversity.py --dataset synth-multiscript-v3 --output docs/datasets/diversity_reports/
```

**Scope**: Applies to ALL datasets with accessible manifests. This will populate Section 2
(14-dimension diversity) with real data instead of 0.0/100 placeholder scores.

**Reference**: `docs/datasets/diversity_reports/orientation_ddr.md` Section 7.3 (cross-dataset note).

---

## P1 Remediation Actions — Significant Gap

Actions that address significant training gaps after P0 is cleared.

### P1-1: iqa-curated — Real-World Bad Mobile Capture Curation

**Dataset**: iqa-curated | **Effort**: 5–8 days | **Wild score after**: ~33 → ~75

**Action**: Source ~2,000 real-world images showing poorly-photographed documents. Prioritize:
book gutter shadow with visible curvature, screen recapture with Moiré patterns, motion-blurred
mobile captures. Annotate all 6 heads (3+ annotators, IAA target SRCC > 0.7).

**Expected coverage**: Closes "Book gutter shadow," "Screen recapture," and improves "Mobile blur"
from partial to full coverage.

---

### P1-2: iqa-synthetic — Staged Fine-Tuning Protocol

**Dataset**: iqa-synthetic | **Effort**: 1–2 days (training time) | **Impact**: Prevents catastrophic forgetting

**Action**: After pre-training on 100K synthetic images, fine-tune using 2-stage protocol:

1. **Linear probing**: Freeze backbone, train only the 6 IQA heads on `iqa-curated` data
2. **Full fine-tuning**: Unfreeze all layers at 10x lower LR to gently adapt to real distribution

**Note**: This is a training strategy, not a dataset metric. It is critical for realizing pre-
training value and avoiding the 5:1 synthetic-to-real ratio catastrophic forgetting risk.

---

### P1-3: skew — Angle Distribution Rebalancing + Confidence Filter Removal

**Dataset**: skew | **Effort**: 1 week code + 2–3 weeks HITL setup

**Problem**: 70.8% within-0.5-deg metric is a diagnostic signal: errors concentrate in the high-
density near-zero region where OCR line segmentation is most sensitive. Confidence filter removes
~30% of natural scans — the exact faded/low-contrast cases the model needs for training.

**Action**:

1. Rebalance angle sampling: 75% Gaussian(0°, σ=0.75°), 25% uniform ±45°
2. Disable confidence filter; route previously-filtered images to HITL review
3. Re-split natural scan sources at document level (not page level) to prevent same-document
   train/test contamination

---

### P1-4: skew — Combined Skew+Warping Synthetic Generation

**Dataset**: skew | **Effort**: 1–2 weeks

**Action**: Generate 10,000 images with combined skew+warping (OpenCV `remap` mesh warps,
Perlin noise shadow overlays). Add multi-scale training (256–512px random crop) to eliminate
fixed 384×384 resolution bias.

---

### P1-5: handwriting — FUNSD Expansion + Synthetic Form Generation

**Dataset**: handwriting | **Effort**: 2–4 weeks

**Action**: Supplement FUNSD's 199 images with:

1. Internal form scans (any available enterprise forms/contracts/invoices)
2. Synthetic form generation: populate form templates with handwritten inserts from CASIA-HWDB
   and KHATT samples to create hybrid (typed + handwritten) documents
3. Target 5,000+ form fill-in examples to reach minimum class representation

---

### P1-6: capture-method — Modern CIS Scanner Data Acquisition

**Dataset**: capture-method | **Effort**: 2–3 weeks | **Wild score after**: Covers `Modern flatbed scanner` condition

**Action**:

1. Commission a commercial scanning bureau to scan 200–500 physical documents on modern
   office equipment (CIS sensors, 2020+). Document make/model/year in L2 metadata.
2. Build automated screen recapture pipeline: smartphone on fixed tripod photographs 3 different
   monitor types (4K IPS, 1080p laptop, OLED) displaying documents. Generates moiré/subpixel
   artifacts cheaply at scale.
3. Target: 2,000 `scanned_flatbed` (CIS) + 300 `screen_recapture` images

---

### P1-7: synth-multiscript-v3 — Targeted Fill Run for 17 Under-Represented Scripts

**Dataset**: synth-multiscript-v3 | **Effort**: 4–6 hours compute (GPU VM or local P40)

**Problem**: 8.6x class imbalance (Arab 49K vs Thai 5.7K). 17 of 27 scripts are below the 12,963
target. Over-represented: Arab (49K = 3.8x), Deva (19K), Hans (17K).

**Action**:

1. Run `scripts/audit_v3_per_script_counts.py` to generate per-script deficit JSON
2. Run targeted fill using `--resume-from-audit` flag (skips scripts already at target)
3. Fix `chunk_per_script` bug in `generate_base_dataset_v3.py:811` first (see Part 9)
4. Target: each of 27 scripts within ±10% of 12,963

---

### P1-8: orientation — RTL Document Expansion

**Dataset**: orientation | **Effort**: 2–3 weeks

**Problem**: Arabic/Hebrew documents represent ~500 of 50K samples (1%). Non-Latin RTL
whitespace cues for orientation are absent at this scale.

**Action**: Increase Arabic/Hebrew orientation examples from ~500 to ≥5,000 (10%) using
synth-multiscript-v3 Arab/Hebr subsets rotated to all 4 orientations.

---

## P2 Remediation Actions — Improvement

Actions that improve diversity but are not blocking training.

### P2-1: iqa-curated — Fax + Aged Document Augmentations

**Dataset**: iqa-curated | **Effort**: 2–3 days | **Wild score after**: ~75 → ~92

**Action**: Implement deterministic augmentation functions:

- **Aged documents**: Yellowing (HSV shift), contrast reduction (gamma ~1.4), foxing spot overlays
- **Fax artifacts**: Otsu binarization, horizontal dithering noise, salt-and-pepper at p=0.02–0.05
- Target 1K–2K examples per category; use generation parameters as tier_0 pseudo-labels

---

### P2-2: resolution-quality — Redesign Label Schema

**Dataset**: resolution-quality | **Effort**: 3–5 days design + re-labeling time

**Problem**: `char_height` measures geometric character size, not perceptual sharpness (r=0.18
MOS correlation). The metric cannot distinguish upscaled rasters from genuinely high-res images.

**Action**: Replace char_height buckets with a 1-5 perceptual MOS rubric with visual anchors.
Run a 1K pilot validation before committing to re-labeling the full 30K corpus. Consider using
VLM-assisted labeling (validated at SRCC=0.53 for non-rotated images — see IQA VLM pilot results).

---

### P2-3: orientation — Symmetric Document Generation

**Dataset**: orientation | **Effort**: 0.5 days

**Problem**: Symmetric documents (cover pages, blank forms, figures-only pages) are completely
absent. The model will make high-confidence errors on 0°/180° for symmetric layouts.

**Action**: Curate 500 symmetric pages from DocLayNet (cover + title pages) + scan blank form
templates. Mark `ood_categories=["ood_geometry"]` for evaluation-only use.

---

### P2-4: skew — Residual Error Analysis

**Dataset**: skew | **Effort**: 3 days

**Action**: Generate residual plot of `(predicted − true)` vs `true angle`, segmented by source
and script. Confirms or refutes the heteroscedastic error hypothesis. Results inform P1-3 and
P1-4 prioritization. Add to DDR Section 2 metadata once manifest ingestion is fixed (P0-8).

---

### P2-5: synth-multiscript-v3 — Rename Kore to Hang

**Dataset**: synth-multiscript-v3 | **Effort**: Trivial (1 day)

**Action**: Rename all `Kore` labeled entries to `Hang` (correct ISO 15924 code for Korean Hangul).
Update `scripts/audit_v3_per_script_counts.py` and `scripts/evaluate_dataset_diversity.py`
V3_SCRIPTS list: replace `Cher`, `Cans`, `Hang` with actual GCS scripts `Armn`, `Grek`, `Kore`
(or `Hang` post-rename).

---

### P2-6: capture-method — Synthetic ADF Augmentation Pipeline

**Dataset**: capture-method | **Effort**: 2–3 weeks

**Action**: Build targeted augmentation pipeline to simulate ADF artifacts:

1. `Perspective`/`Affine` transforms for geometric skew/shear from paper feed
2. `ElasticTransform` (high alpha, low sigma) near vertical edges for paper curl
3. Randomized vertical line overlays for roller dust artifacts
4. Random JPEG compression quality variation
Apply to 2,000 `born_digital` + newly acquired `scanned_flatbed` images.

---

### P2-7: All Datasets — 14-Dimension Metadata Population

**Effort**: 2–3 days per dataset (after P0-8 manifest ingestion fix)

**Action**: Once manifest ingestion works (P0-8), populate Section 2 metrics for all datasets by
running `scripts/evaluate_dataset_diversity.py` with correct path mapping. This unlocks the full
100-point DDR scoring and chi-square uniformity tests.

---

## Blocked Actions — Awaiting Prerequisites

The following remediation actions are blocked pending infrastructure or physical hardware:

### BLOCKED-1: shadow + warping DDR Generation

**Blocked by**: GPU labeling scripts (`label_shadow_severity.py`, `label_warping_severity.py`)
not yet run. `shadow_severity` and `warping_severity` fields absent from L2 metadata.

**Unblocking action**: Run severity labeling scripts on GPU VM (Vultr A100) or local P40 once
installed. See plan Part 6A for exact commands.

---

### BLOCKED-2: Phase 1 Synthetic View Generation

**Blocked by**: GPU access required for `generate_v3_shadow_view.py`, `generate_v3_warping_view.py`,
`derive_v3_orientation_view.py`, `build_orientation_real_component.py`.

**Unblocking action**: Run Phase 1 scripts on GPU VM after BLOCKED-1. See plan Part 6B.

---

### BLOCKED-3: OOD Physical Collection

**Blocked by**: Requires physical equipment (modern flatbed scanner, tripod rig) and time.

**Scope**: Screen recaptures (300 images), modern flatbed scans (2,000 images), ADF scans
(1,000 images), book gutter shadow photographs (500 images).

See plan Part 7C for complete physical collection checklist.

---

## Remediation Sequencing Diagram

```text
Week 1:
  ├── P0-2: iqa-synthetic calibration study (500 pilot images + MOS scoring)
  ├── P0-4: handwriting taxonomy definition (no data acquisition until done)
  ├── P0-6: capture-method 4-class head redesign (1-2 days)
  ├── P0-7: synth-multiscript-v3 script alignment decisions
  └── P0-8: manifest ingestion fix (unblocks all Section 2 scoring)

Week 2:
  ├── P0-1: iqa-curated compound augmentation pipeline (uses P0-8 results)
  ├── P0-3: iqa-synthetic causal distortion pipeline (uses P0-2 calibration)
  ├── P2-5: synth-multiscript-v3 Kore → Hang rename
  └── P1-3: skew angle rebalancing + confidence filter removal (code)

Week 3-4:
  ├── P1-7: synth-multiscript-v3 targeted fill run (after P0-7 decisions)
  ├── P1-4: skew compound skew+warping generation
  ├── P2-3: orientation symmetric document curation
  └── P2-1: iqa-curated fax + aged augmentations

Week 5-8:
  ├── P0-5: handwriting dataset acquisition (CASIA-HWDB → KHATT → FUNSD+ → IIIT-INDIC → HKR)
  ├── P1-5: handwriting FUNSD expansion + synthetic forms
  ├── P1-6: capture-method CIS scanner sourcing + screen recapture pipeline
  ├── P1-8: orientation RTL expansion
  └── P2-6: capture-method ADF augmentation pipeline

After GPU hardware available:
  ├── BLOCKED-1: shadow + warping severity labeling (GPU VM / local P40)
  ├── BLOCKED-2: Phase 1 synthetic view generation
  └── Generate shadow + warping DDRs (DDR #9 and #10)
```

---

## Consolidated Effort Estimate

| Priority | Actions | Total Effort |
| --- | --- | --- |
| P0 | 8 actions | 4–10 days (code) + 4–6 weeks (handwriting acquisition) |
| P1 | 8 actions | 3–6 weeks |
| P2 | 7 actions | 1–2 weeks |
| Blocked | 3 actions | Depends on hardware/VM availability |

**Minimum viable remediation before training any model**:

- iqa-curated: P0-1 + P1-1 (8–13 days)
- iqa-synthetic: P0-2 + P0-3 (9–13 days, sequential)
- handwriting: P0-4 + P0-5 (4–6 weeks, acquisition-limited)
- capture-method: P0-6 (1–2 days)
- skew: P1-3 + P2-4 residual analysis (2 weeks)
- orientation: P0-8 + P1-8 (3 weeks)
- synth-multiscript-v3: P0-7 + P2-5 + P1-7 (1 sprint + 4–6h compute)
- resolution-quality: P2-2 design only (3–5 days design, then re-labeling)

---

## Cross-Dataset Themes

These themes appear across multiple datasets and represent systemic gaps in the data pipeline:

**1. Confidence filter bias (orientation, skew)**: Filtering out low-confidence examples
systematically removes the hardest, most informative training cases. Recommended mitigation:
route filtered examples to HITL review rather than discard.

**2. Single-source academic datasets (iqa-curated, capture-method, skew)**: Overreliance on
OHR-Bench (research PDFs), RVL-CDIP (1990s CCD scans), and font-rendered synthetics introduces
domain shift. Each dataset needs real-world "bad capture" supplementation.

**3. Missing joint distribution coverage (iqa-curated, iqa-synthetic)**: Multi-head models
require compound distortion examples — not just per-head coverage. This is the most critical
structural flaw across the IQA pipeline.

**4. Manifest path inaccessibility (all datasets)**: WSL cannot access `E:/` or `gs://` paths
directly, causing Section 2 diversity metrics to fail silently with 0.0/100. Fix P0-8 to unblock
meaningful scoring for all datasets.

**5. Pre-acquisition auditing working correctly**: The DDR process correctly identified all
critical gaps before data acquisition or training. The 0.0/100 automated scores reflect
measurement infrastructure limitations, not necessarily data quality failures. The wild condition
coverage matrix (Section 1) provides reliable findings independent of this limitation.

---

## DDR Source References

| Dataset | DDR File | Section 7 Status |
| --- | --- | --- |
| orientation | `docs/datasets/diversity_reports/orientation_ddr.md` | ✅ Complete (aff1826) |
| skew | `docs/datasets/diversity_reports/skew_ddr.md` | ✅ Complete (aff1826) |
| resolution-quality | `docs/datasets/diversity_reports/resolution_quality_ddr.md` | ✅ Complete (a5d2ad9) |
| iqa-curated | `docs/datasets/diversity_reports/iqa_curated_ddr.md` | ✅ Complete (a6e9e0b) |
| iqa-synthetic | `docs/datasets/diversity_reports/iqa_synthetic_ddr.md` | ✅ Complete (a6e9e0b) |
| handwriting | `docs/datasets/diversity_reports/handwriting_ddr.md` | ✅ Complete (ad61ba6) |
| capture-method | `docs/datasets/diversity_reports/capture_method_ddr.md` | ✅ Complete (ad61ba6) |
| synth-multiscript-v3 | `docs/datasets/diversity_reports/synth_multiscript_v3_ddr.md` | ✅ Complete (a5d2ad9) |
| shadow | `docs/datasets/diversity_reports/shadow_ddr.md` | ❌ Not generated (blocked) |
| warping | `docs/datasets/diversity_reports/warping_ddr.md` | ❌ Not generated (blocked) |

---

*Generated by consolidating 8 DDR Section 7 consensus reviews — 2026-02-21*
*All Section 7 reviews: `google/gemini-2.5-pro` (thinking_mode: high) via `mcp__pal__chat`*
*Fallback from `mcp__pal__tiered_consensus` Level 2 (returned configuration metadata only)*
