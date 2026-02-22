# Dataset Completeness Handoff

> **Date**: 2026-02-21
> **Purpose**: Gap analysis for the MobileNetV4 + SigLIP 2 multi-task training pipeline
> **Source documents**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md),
> [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md),
> [DIVERSITY_REMEDIATION_PLAN.md](DIVERSITY_REMEDIATION_PLAN.md),
> [docs/datasets/diversity_reports/](../datasets/diversity_reports/)

---

## 1. What We Are Training

Two models. Each requires separate training datasets.

### MobileNetV4-Conv-S (fast pre-correction gate, ~3ms GPU)

| Head | Task | Dataset |
| --- | --- | --- |
| H1: Orientation | 4-class (0/90/180/270) | orientation (50K) |
| H2: Skew | Regression ±10° | skew (90K) |
| H3: Resolution quality | Regression 0–1 (char-height-aware) | resolution-quality (30K target) |

### SigLIP 2 NAFlex (full analysis, ~50ms GPU)

| Group | Heads | Task | Dataset |
| --- | --- | --- | --- |
| G1: IQA | blur, noise, contrast, skew\_severity, compression, overall | 6× regression 0–1 | iqa-curated (16K hard) + iqa-synthetic (100K planned) |
| G2: Script | script\_code | 19-class classification | synth-multiscript-v3 + MDIW13 + COCO-Text etc. |
| G3: Orientation + Skew | orientation, residual\_skew | 4-class + regression | Shared with MNV4 datasets |
| G4: Handwriting | presence, legibility, content\_type, presence\_score, legibility\_score | 3 cls + 2 reg | handwriting (60K) |
| G5: Page Attributes | capture\_method, shadow, warping, resolution\_quality, code\_confidence | 1 cls + 4 reg | capture-method (50K) + shadow (18K) + warping (24K) |

---

## 2. Dataset Status at a Glance

| # | Dataset | Target | Current | Source Data Status | Labels Status | Gap Type |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **orientation** | 50K | 50K old; rebuilding | ✅ All sources on GCS | ✅ Exact by construction | Engineering (scripts written, execution pending) |
| 2 | **skew** | 90K | **90K ✅ COMPLETE** | ✅ GCS | ✅ Hough-derived | None — model trained |
| 3 | **resolution-quality** | 30K | 5.5K done | ✅ Sources available locally | ⚠️ V1 labels imprecise (V2 strategy ready) | Engineering (re-labeling + GPU) |
| 4 | **iqa-curated** | 16–25K | Partial | ✅ DIQA-5000, OHR-Bench, RealDAE on disk | ⚠️ Missing compound distortions | Engineering (augmentation pipeline) |
| 5 | **iqa-synthetic** | 100K | 0 | Will derive from synth-multiscript-v3 | ❌ Calibration study required first | Engineering (P0: calibration study before generation) |
| 6 | **synth-multiscript-v3** | 108K (sub-sampled for script training) | 190K on GCS but imbalanced | ✅ GCS | ⚠️ 8.6× class imbalance (generator bug) | Engineering (rebalancing fill run) |
| 7 | **handwriting** | 60K | 0 assembled | ⚠️ 80% exists; 20% missing (CJK + Devanagari hw) | ❌ Label harmonization not done | Mixed: engineering + limited acquisition |
| 8 | **capture-method** | 50K | 0 assembled | ⚠️ 85% exists; ADF/FAX need heuristic labeling | ❌ ADF/FAX not labeled | Engineering (labeling scripts) |
| 9 | **shadow** | 18K | 0 assembled | ✅ sd7k + wsrd + v3 on GCS/disk | ❌ severity labels not yet run | Engineering (GPU labeling scripts) |
| 10 | **warping** | 24K | 0 assembled | ✅ wsrd + anyphotodoc6300 + docalign12k + warpdoc | ❌ severity labels not yet run | Engineering (GPU labeling scripts) |

**Key finding**: 7 of 10 datasets are primarily engineering tasks against data that already exists.
Datasets 1, 6, and part of 7 have genuine data gaps.

---

## 3. Datasets Ready to Assemble (Engineering Only)

No new data acquisition required for these. Gaps are labeling scripts, augmentation pipelines,
or GPU compute.

### 3.1 orientation (50K) — Scripts Written, Execution Pending

**What exists**: DocLayNet PDFs on GCS, RVL-CDIP scans on GCS, synth-multiscript-v3 on GCS.

**What's missing**: Script execution (requires data transfer to Modal volume or GPU VM).

**Action**: Run `scripts/build_orientation_real_component.py` +
`scripts/derive_v3_orientation_view.py`, then `prepare_multitask_datasets.py orientation`.

**Note**: Old 50K dataset at `E:\03_training_datasets\orientation\` is Latin-heavy. The
new hybrid addresses this — do not train on the old dataset.

---

### 3.2 skew (90K) — DONE

Nothing to do. Best trained model: MobileNetV4-Conv-S @ 224px, 50 epochs.
Val MAE=0.837, test MAE=0.956, SRCC=0.936, orient_acc=99.5%.
Checkpoint: `best_model.pt` (epoch 47, run ID `20260212_155402`).

**Remaining gap** (P1, not blocking): angle distribution near-zero is head-heavy; 70.8%
within-0.5° metric suggests errors concentrate where OCR line segmentation is most sensitive.
See `DIVERSITY_REMEDIATION_PLAN.md` P1-3.

---

### 3.3 iqa-curated (16–25K) — Augmentation Pipeline Needed

**What exists**: DIQA-5000 (5.5K), OHR-Bench (8.5K), RealDAE (1.2K), SmartDoc-QA (4.3K),
MIDV500 (3.6K) — all on disk or GCS.

**What's missing**: Compound distortion examples (the most critical gap). Single-distortion
training teaches the wrong prior for multi-head IQA.

**Action (P0-1)**: Build a compound augmentation pipeline that applies 2–5 simultaneous
distortions to clean OHR-Bench base images. Use applied parameters as per-head pseudo-labels.
Target 5K–10K compound examples. Does not require any new data.

**VLM labeling status**: 200-image pilot complete (SRCC=0.53 non-rotated). Prompt V2 needed
before scaling to 2–5K. See `results/iqa_vlm_labeling/`.

---

### 3.4 iqa-synthetic (100K) — Calibration Study First

**What exists**: Synth pipeline infrastructure ready. Source: synth-multiscript-v3 + Augraphy.

**CRITICAL GATE (P0-2)**: Do NOT generate 100K images until calibration study validates that
parameter-to-label mapping is non-spurious. Simple `blur_sigma=2.0 → blur=0.6` is resolution-
and content-dependent and non-linear. Generating 100K with bad labels and discovering this
post-training costs weeks of GPU time.

**Action**: Generate 500-image calibration pilot → 3+ annotators MOS → fit calibration model
→ only then bulk-generate with calibrated tier_1 labels.

---

### 3.5 shadow (18K) and warping (24K) — GPU Labeling Scripts Needed

**What exists (shadow)**: sd7k (7,239 paired), wsrd (4,500 paired), SmartDoc-QA negatives,
MIDV500 negatives — all on disk. v3 synthetic shadow script written.

**What exists (warping)**: anyphotodoc6300 (6,306 paired), warpdoc (1,020 paired),
docalign12k (~12,000 pairs), docreal (200), drccbi (325) — all on disk.
v3 synthetic warping script written.

**What's missing**: `shadow_severity` and `warping_severity` fields not yet populated in
L2 metadata. Labeling scripts (`label_shadow_severity.py`, `label_warping_severity.py`) need
GPU VM (Vultr A100) or local P40.

**Action**: Run labeling scripts on GPU → re-run `prepare_multitask_datasets.py shadow/warping`
dry-run (must show >0 real records) → generate DDRs.

**Do NOT use SSIM** for either shadow or warping labels. SSIM measures structural similarity, not
shadow/warping severity — it penalizes blur, noise, and compression equally.

---

### 3.6 capture-method (50K) — Labeling + Class Collapse Needed

**What exists**:
- `BORN_DIGITAL` (15K target): DocLayNet, PubTabNet, FinTabNet ✅ ready (>600K available)
- `SCANNER_FLATBED` (12.5K target): RVL-CDIP, Tobacco800, NIST SD-2/SD-6, MDIW13 ✅ ready
- `CAMERA_PROFESSIONAL` (5K target): MIDV500, SmartDoc-QA ✅ ready
- `CAMERA_SMARTPHONE` (5K target): SROIE, RealDAE, MLT19 camera subset ≈ 11K available ✅ (tight)
- `SYNTHETIC` (7.5K target): DocSynth300K, synth-multiscript-v3 ✅ ready
- `SCANNER_ADF` (2.5K target): RVL-CDIP subset — **needs heuristic labeling** (edge feed marks, skew patterns)
- `FAX` (2.5K target): RVL-CDIP doc type labels — **needs manual propagation** (~500 manually labeled → propagate)

**P0 decision required (P0-6)**: Collapse to 4-class for v1 (`scanned_flatbed`, `scanned_adf`,
`camera_capture`, `born_digital`). The 7-class head cannot be learned at current coverage imbalance.
The v1 model needs only these 4 classes. Expand to 7 after ≥2K examples per fine-grained class.

**What is NOT needed**: Physical scanning of new documents for v1.

---

## 4. Datasets With Genuine Data Gaps

These require either new dataset downloads or targeted generation.

### 4.1 synth-multiscript-v3 (190K on GCS, target ~350K balanced)

**Gap**: 8.6× class imbalance from generator bug at line 811. Arab 49K (3.8× target), Thai 5.7K
(0.44× target). 17 of 27 scripts are below 12,963 target.

**Three script alignment decisions needed before any fill run**:

| Decision | Options | Implication |
| --- | --- | --- |
| Cher (Cherokee) + Cans (Canadian Aboriginal) | Include → acquire fonts first; or exclude | Font acquisition needed if included |
| Armn (Armenian) + Grek (Greek) — unexpected in GCS | Keep → 29-class model; or remove | Must decide before training script head |
| Kore → Hang | Rename to correct ISO 15924 code | Trivial — do immediately |

**What is NOT needed**: New source data. The fill run uses the existing Augraphy text synthesis
pipeline with already-installed fonts, targeting specific script deficits.

**Tibetan special case**: TibHCR has 141K CHARACTER images but ~0 full-page documents. Only ~200
real Bhutan docs available. The 4K target for TIBT is at risk. Pursue BDRC (Tibetan Buddhist
Resource Center) partnership OR accept TIBT as ~80% synthetic (similar to Hebrew/Greek).

### 4.2 handwriting (60K) — 80% Assembleable, 20% Genuine Gap

**What already exists** in the catalog and is sufficient:

| Source | Contribution | Status |
| --- | --- | --- |
| HierText (word-level hw labels) | ~8K Latin, word-level hw/legible bool | ✅ in catalog |
| COCO-Text (machine/handwritten class) | ~15K mixed, primarily Latin | ✅ in catalog |
| IAM (657 writers, English) | ~5K Latin cursive | ✅ in catalog |
| Muharaf (Arabic manuscripts) | ~5K Arabic cursive handwriting | ✅ in catalog |
| NIST SD-19 (census forms) | ~2K Latin handwriting forms | ✅ in catalog |
| FUNSD (form fill-in) | 199 mixed print+handwriting | ✅ in catalog |
| DocLayNet (printed-only negatives) | ~15K NONE class | ✅ in catalog |
| PubTabNet (table negatives) | ~5K NONE class | ✅ in catalog |
| **Subtotal** | **~55K Latin/Arabic** | |

**Script coverage achievable without new acquisition**:

| Script | Target (% of 60K) | Available | Gap |
| --- | --- | --- | --- |
| Latin (Print + Cursive) | 40% = 24K | ~28K (HierText + COCO-Text + IAM + NIST) | ✅ Sufficient |
| Arabic (Naskh/Ruqah) | 15% = 9K | ~5K (Muharaf) | ⚠️ Short ~4K |
| Devanagari | 10% = 6K | ~1K (Nepali Handwritten, if available) | ❌ Short ~5K |
| CJK (Simplified + Traditional) | 10% = 6K | ~0 | ❌ Missing entirely |
| Other + NONE class | 25% = 15K | ~20K (negatives + PUCIT-OHUL Urdu) | ✅ Sufficient |

**Genuine acquisition gaps (CJK and Devanagari handwriting)**:

| What to Get | Source | License | Size Needed |
| --- | --- | --- | --- |
| Chinese handwritten pages | CASIA-HWDB (NLPR) | Free academic, request form | ~5K pages |
| Devanagari handwritten | IIIT-INDIC (IIIT Hyderabad) | Free academic | ~3K pages |
| Additional Arabic cursive | KHATT (khatt.ideas2serve.net) | Free academic | ~4K pages |

**Label harmonization work** (required regardless of acquisition): The three handwriting heads use
different classification taxonomies than the raw source labels. A harmonization pipeline must map:
HierText word-level `handwritten: bool` → page-level presence class; IAM line-level data → density
tier; IAM transcription error rates → legibility class. This is engineering, not annotation.

**Alternative if CJK acquisition is not possible**: Accept the CJK handwriting gap and train G4
heads as Latin/Arabic-biased. Mark model card accordingly. CJK handwriting detection will have high
false negative rate. Adjust `handwriting_script` taxonomy accordingly (remove `CJK-Simplified` and
`CJK-Traditional` from fine-grained classes).

---

### 4.3 resolution-quality (30K) — Label Quality Problem More Than Data Gap

**What exists**: DIQA-5000 (5.5K labeled), OHR-Bench (8.5K), RealDAE (1.2K), SmartDoc-QA (4.3K),
MIDV500 (3.6K), synth-multiscript-v3 samples — all on disk. Sources are sufficient to reach 30K.

**Real problem**: V1 char_height-based labels have IQR=9.0px (target 2–3px) and r=0.18 MOS
correlation. The labels don't reflect perceptual sharpness. They can't distinguish upscaled rasters
from genuinely high-resolution images (a critical production failure).

**Action (P2-2)**: V2 label strategy uses Sauvola binarization + projection profiles (see
`RESOLUTION_QUALITY_V2_STRATEGY.md`). Run V2 labeler on existing DIQA-5000 images first as
validation — if precision improves to target (IQR 2–3px), expand to full 30K corpus.

---

### 4.4 code-detection (~10K) — Generation Required

**Gap**: No existing dataset has code block annotations at the page level.

**What's needed**:
- ~4K GitHub code screenshots via Playwright or carbon-now-cli (realistic syntax-highlighted renders)
- ~2K technical document pages with code from multimodal-textbook, mathverse (may be in catalog)
- ~3K born-digital without code (negatives) from DocLayNet, FinTabNet ✅ already available
- ~1K synthetic code renders at various DPI/fonts

**Effort**: 3–5 days engineering (Playwright automation, font/theme variation, multi-language coverage).
No dataset requests required.

---

## 5. What Cannot Be Obtained Easily

These represent genuine constraints, not just engineering effort:

| Gap | Why Hard | Mitigation |
| --- | --- | --- |
| CJK handwriting at page level | CASIA-HWDB requires institutional request to CASIA-NLPR (China) | Accept gap; mark model card; or use synth-multiscript rendered handwriting-style fonts as weak proxy |
| Devanagari handwriting | IIIT-INDIC requires IIIT Hyderabad contact | Nepali Handwritten (958 pages) + synthetic proxy |
| Modern CIS scanner data | Requires physical hardware access (2020+ CIS flatbed) | Defer to v2; use synthetic ADF augmentation (P2-6) |
| Multiply-distorted real documents | Cannot reliably source (rare, inconsistent labeling) | Generate via compound augmentation pipeline (P0-1) |
| Fax artifacts (real fax documents) | Physical fax infrastructure required | RVL-CDIP fax subset + augmentation (halftone/banding simulation) |
| Mongolian, Syriac, Georgian | Reserved as OOD-Script anchors — NEVER in training | This is intentional by design |

---

## 6. Priority Order for Assembly

### Week 1 — No GPU, No New Data

1. **P0-6**: Make the 4-class capture-method head decision (1–2 hours)
2. **P0-7**: Resolve the three synth-multiscript-v3 script alignment decisions (1 sprint)
3. **P2-5**: Rename `Kore` → `Hang` in GCS metadata (trivial, do now)
4. **P0-4**: Finalize handwriting label harmonization pipeline design (taxonomy done;
   now specify exact field mappings from each source to each head)
5. **P0-2**: Launch iqa-synthetic calibration study (500 images, 3 annotators, ACR-HR protocol)

### Week 2 — GPU Available

6. Run `label_shadow_severity.py` and `label_warping_severity.py` on GPU VM → unblocks datasets 9 + 10
7. Run Phase 1 generation scripts → orientation hybrid (dataset 1), shadow (dataset 9), warping (dataset 10)
8. Fix generator bug at `scripts/generate_base_dataset_v3.py:811` → run targeted fill for synth-v3

### Weeks 3–4 — Parallel Tracks

9. **capture-method**: Write ADF/FAX heuristic labeler → assemble 50K manifest
10. **iqa-curated**: Build compound augmentation pipeline (P0-1)
11. **handwriting**: Start label harmonization pipeline (maps existing source labels → 5 head schema)
12. **resolution-quality**: Run V2 labeler on DIQA-5000 → validate precision before expanding to 30K

### Weeks 5–8 — Acquisition (if approved)

13. Submit CASIA-HWDB + KHATT + IIIT-INDIC requests
14. If acquisition fails: accept Latin/Arabic-only handwriting head; document in model card

---

## 7. Summary: What Requires New Dataset Downloads

| Dataset to Acquire | For Head | Urgency | Fallback if Unavailable |
| --- | --- | --- | --- |
| CASIA-HWDB (CJK handwriting) | G4 handwriting | High | Train without CJK; mark model card |
| KHATT (Arabic cursive) | G4 handwriting | High | Muharaf alone (~5K, below 9K target) |
| IIIT-INDIC (Devanagari hw) | G4 handwriting | Medium | Nepali Handwritten (958 pages) only |
| HKR (Cyrillic handwriting) | G4 handwriting | Low | Accept gap; Cyrillic printed present via synth |

Everything else (orientation, skew ✅, resolution-quality, iqa-curated, iqa-synthetic,
synth-multiscript-v3, capture-method, shadow, warping, code-detection) can be assembled
from data already on disk or GCS. The work is engineering: labeling scripts, augmentation
pipelines, label harmonization, and GPU compute time.

---

*Generated 2026-02-21 | Synthesized from SIGLIP2_MULTITASK_REQUIREMENTS.md,
DATASET_DIVERSITY_REQUIREMENTS.md, and all 8 DDR reports*
