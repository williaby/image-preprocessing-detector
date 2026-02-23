# Head Adequacy Review: legibility_reg (SIG-G4-5)

> **Status**: Reviewed — Blocked
> **Version**: 1.1
> **Created**: 2026-02-22
> **Updated**: 2026-02-23
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: E — Handwriting
> **Adequacy**: Blocked

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G4-5 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | legibility_reg (also written as handwriting_legibility_score) |
| Task Type | Regression — 0-1 continuous (0 = illegible, 1 = perfect legibility) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P1 |
| Performance Target | Pearson r >= 0.80 on OOD holdout (see Section 9 — target revised) |
| Primary L2 Field | `handwriting_assessment.legibility_score` (float 0-1) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5); SIG-G4-2 (legibility_cls is the discretized version) |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.legibility_score` (float 0.0–1.0; 0 = illegible, 1 = perfect legibility)

**Confidence Threshold**: >= 0.7 (tier_1_annotation or better)

**Label Provenance**: No dataset has direct human legibility ratings as continuous ground truth.
VLM labeling (5-point MOS-like scale normalized to 0-1) is the only tractable path. This
introduces model-in-the-loop bias and limits the achievable evaluation SRCC against human
ratings.

**Critical dependency on SIG-G4-2**: The legibility_reg head requires the same labels as
legibility_cls, but in continuous form. Every blocker that applies to SIG-G4-2 (legibility_cls)
applies here, compounded by additional regression-specific validity concerns documented in
Section 8.

### Proposed Score-to-Class Mapping

The scaffold proposed this linear interpolation to derive continuous scores from ordinal classes:

| Score Range | Legibility Class | Proposed Center | Inter-Class Distance |
| --- | --- | --- | --- |
| 0.00–0.10 | ILLEGIBLE | 0.10 (target anchor) | — |
| 0.10–0.30 | POOR | 0.25 | 0.15 |
| 0.30–0.55 | FAIR | 0.45 | 0.20 |
| 0.55–0.80 | GOOD | 0.70 | 0.25 |
| 0.80–1.00 | EXCELLENT | 0.95 | 0.25 |
| N/A | N/A | sentinel (masked, NOT 0.0) | — |

**Critical flaw in this mapping**: The inter-class perceptual distances are assumed equal (0.15–
0.25 per step) with no empirical basis. Legibility perception is non-linear: the gap between
ILLEGIBLE and POOR is perceptually much larger than the gap between GOOD and EXCELLENT. A linear
interpolation systematically underestimates the lower end of the scale and overestimates the
upper end. No human MOS study exists to calibrate these anchors.

**N_A sentinel warning**: Using N_A=0.0 as a sentinel value (as written in the scaffold table)
would train the model to predict near-zero scores for printed pages with no handwriting. This
is a latent label consistency defect. The correct implementation uses masked loss on N_A images
(loss weight = 0) with a sentinel value of -1.0, not 0.0.

### Label Derivation Hierarchy

| Method | Datasets | Reliability | Confidence |
| --- | --- | --- | --- |
| Direct human MOS ratings (multi-rater, continuous) | None identified | Gold standard | tier_0_exact — ABSENT |
| VLM legibility scoring (5-point scale, norm to 0-1) | All handwriting datasets | SRCC ~0.39–0.53 (per IQA VLM pilot) | tier_1_annotation (weak) |
| Class-to-score interpolation from legibility_cls labels | IAM, COCO-Text (after VLM 6-class), Muharaf, PUCIT-OHUL | Low — arbitrary mapping | tier_2_heuristic |
| Corpus-level fixed assignment | IAM (→ 0.90–1.00 fixed), DocLayNet (→ masked N_A) | Low — no within-corpus variance | tier_2_heuristic |

### Candidate Source Datasets

| Dataset | Est. Images | Continuous Score Available | Path to Labels | Key Issues |
| --- | --- | --- | --- | --- |
| IAM Handwriting | ~13,000 pages | No | Fixed 0.90–1.00 heuristic OR per-image VLM | No within-corpus variance; skews entirely to EXCELLENT range; VLM adds noise but resolves flat distribution |
| COCO-Text | 63,686 | No | COCO-Text 3-class → VLM 6-class → class-to-score mapping | Two mapping steps accumulate error; `blurred` category maps to ~0.25–0.45 range; `others` requires full VLM |
| HierText | 8,281 | No | Word-level legibility ratio → VLM for boundary images | Binary word-level signal compressed to continuous page score; loses granularity |
| Muharaf | ~20,000 (GCS-only) | No | Full VLM labeling required | Arabic script — VLM legibility scoring quality for Arabic uncertain; no baseline established |
| PUCIT-OHUL | ~7,000 (GCS-only) | No | Full VLM labeling required | Urdu/Nastaliq script — VLM capability for Nastaliq calligraphic forms unvalidated |
| KHATT | ~5,000 pages | Partial — some page-level quality ratings | Expert rating cross-reference possible | OOD dataset; using for training would contaminate OOD evaluation |
| NIST SD-19 | ~10,000 pages | No | Fixed 0.85–0.95 heuristic | Form entries; per-page variance not measured |
| FUNSD | ~200 pages | No | VLM per-image | Too small for meaningful distribution; GOOD class only |
| DocLayNet / RVL-CDIP | Hundreds of thousands | N/A — no handwriting | N_A masked loss (sentinel -1.0) | Provides N_A training examples via masked loss |

### Usable Pool Summary

- **Total with legibility_score field populated**: 0 — the L2 field `handwriting_assessment.legibility_score`
  is unpopulated for every source dataset.
- **ILLEGIBLE range (0.00–0.20) training examples**: 0 — structural curation bias eliminates
  ILLEGIBLE content from all curated handwriting corpora.
- **POOR range (0.20–0.35) training examples**: Estimated <5% of Muharaf/PUCIT-OHUL after
  VLM labeling — requires VLM labeling pipeline to run first.
- **Training target**: 60,000 images (shared with all G4 heads).
- **Gap at ILLEGIBLE end**: Unresolvable without new dataset acquisition. The model cannot
  learn a regression mapping for a region of the score space with zero training anchors.

### VLM Validation Requirements

Before large-scale VLM labeling, a calibration study is required:

1. Collect human MOS ratings (5-point scale, >= 3 raters) on 300 images spanning all legibility
   levels including ILLEGIBLE examples from KHATT.
2. Run VLM legibility scoring on the same 300 images.
3. Compute VLM-vs-human SRCC. If SRCC < 0.55, the VLM labeling approach is insufficient and
   must be redesigned before large-scale labeling begins.
4. Use human MOS data to empirically calibrate the class-to-score mapping anchors (replacing
   the current arbitrary linear interpolation).

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| HW-LEG-D01 | All datasets | `handwriting_assessment.legibility_score` | Field not populated anywhere — no labels exist | Open |
| HW-LEG-D02 | Class-to-score mapping | N_A sentinel | N_A=0.0 in scaffold table conflicts with masked-loss requirement; must use -1.0 sentinel | Open — latent defect |
| HW-LEG-D03 | IAM | legibility_score | Fixed-range assignment (0.90–1.00) produces no variance signal in EXCELLENT range | Open |
| HW-LEG-D04 | COCO-Text | legibility_score | Two-step mapping (3-class → 6-class → continuous) accumulates quantization error at each step | Open |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-05-A | No dataset has direct human legibility ratings — VLM is the best available method but SRCC=0.39–0.53 is well below the calibration threshold needed for reliable continuous labels | HIGH — Pearson r target of 0.80 may be unachievable against human ratings |
| KI-G4-05-B | ILLEGIBLE range (0.00–0.20) entirely absent from training — structural curation bias in all handwriting corpora | CRITICAL — model cannot learn the low end of the regression scale; will extrapolate incorrectly |
| KI-G4-05-C | Class-to-score linear mapping is empirically unsupported — inter-class perceptual distances are non-uniform | HIGH — systematic bias in labels; model learns an arbitrary scale, not a human-aligned scale |
| KI-G4-05-D | N_A sentinel value inconsistency — scaffold uses 0.0 but masked loss requires -1.0 sentinel | HIGH — if not corrected, trains model to predict near-zero for printed pages |
| KI-G4-05-E | IAA ceiling 60-70% on classification implies continuous score Pearson r ceiling ~0.60–0.65 against human ratings | HIGH — Pearson r >= 0.80 target exceeds theoretical ceiling from label noise alone |

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 60,000 images (shared with all G4 heads) |
| Assembly Status | Blocked — no labels exist, VLM calibration not run, N_A sentinel defect unresolved |
| Current Count | 0 images with valid `handwriting_assessment.legibility_score` field |
| Gold Standard | Human MOS ratings (none collected); VLM scores as proxy (calibration pending) |
| Performance Target | Pearson r >= 0.80 vs human ratings — see Section 9 for revised target recommendation |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Score Distribution Requirements

| Score Range | Legibility Class | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- | --- |
| 0.00–0.20 | ILLEGIBLE | >= 2% (~1,200 images) | Historical manuscripts, medical writing, heavy augmentation of FAIR | CRITICAL — 0 examples; structurally absent from all sources |
| 0.20–0.35 | POOR | >= 5% (~3,000 images) | Muharaf, PUCIT-OHUL (VLM-labeled blurred/degraded subset) | HIGH — requires VLM labeling; count uncertain |
| 0.35–0.55 | FAIR | >= 15% (~9,000 images) | COCO-Text blurred, Muharaf, PUCIT-OHUL (VLM-labeled) | HIGH — requires VLM |
| 0.55–0.80 | GOOD | >= 30% (~18,000 images) | COCO-Text clear, HierText (VLM-labeled) | MEDIUM — VLM quality for this range likely adequate |
| 0.80–1.00 | EXCELLENT | >= 40% (~24,000 images) | IAM (heuristic or VLM), NIST SD-19 | LOW — well covered structurally |
| N/A | N/A (no HW) | Set by G4-1 NONE | DocLayNet, RVL-CDIP (masked loss) | N/A — excluded from regression loss |

**Blockers**:

- `handwriting_assessment.legibility_score` L2 field unpopulated for all datasets
- VLM calibration study against human MOS not run
- Class-to-score mapping formula not empirically validated
- ILLEGIBLE range (0.00–0.20) has zero training anchors — data void unresolvable without new acquisition
- N_A sentinel value defect (0.0 vs -1.0) must be corrected before any assembly
- `handwriting` subcommand of `prepare_multitask_datasets.py` not implemented

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 0 / 100 (dataset not assembled; all assessments are pre-assembly projections)

**Key observation**: The score_distribution dimension (legibility_score range coverage) is the
most critical for this regression head. Without examples in the 0.00–0.35 range, no amount
of improvement in other dimensions can rescue the head's ability to predict low legibility
scores.

| Dimension | L2 Field | Relevance | Target | Current Estimate | Score |
| --- | --- | --- | --- | --- | --- |
| score_distribution | `handwriting_assessment.legibility_score` | CRITICAL | Full 0–1 range; gap in 0.00–0.35 is fatal | 0 — field unpopulated | 0 |
| script_code | `language.script_code` | HIGH | >= 4 scripts (LATN, ARAB, DEVA, HANS) | LATN (IAM, HierText, COCO-Text), ARAB (Muharaf); CJK/Deva absent | 0 |
| capture_method | `capture_method.method` | HIGH | >= 3 methods (scanner, camera, born_digital) | scanner (IAM), camera (COCO-Text/HierText), born_digital (negatives) | 0 |
| degradation | `quality.degradations` | CRITICAL | >= 4 types (blur, noise, ink_fading, bleed_through) | Degradation directly drives legibility score; currently absent from HW sources | 0 |
| document_age | `image_properties.document_age` | HIGH | All 3 ages (modern, aged, historical) | Modern only; historical is the primary ILLEGIBLE/POOR source | 0 |
| domain | `domain.level1` | MEDIUM | >= 5 domains | Academic (IAM), scene text (COCO-Text, HierText); limited domain spread | 0 |
| color_mode | `image_properties.color_mode` | MEDIUM | >= 2 modes (color, grayscale) | Grayscale dominant (IAM, NIST-SD2); some color in scene text | 0 |
| writing_instrument | (no dedicated L2 field) | HIGH | Pen, pencil, marker — each affects legibility independently | Not tracked; pencil (lower contrast) and faded ink (aging) absent | 0 |
| background_complexity | `image_properties.background` | MEDIUM | Plain and complex (e.g., forms, lined paper) | Plain dominant; complex background affects legibility perception | 0 |
| mixed_content | `handwriting_assessment.is_mixed` | MEDIUM | Both pure HW and printed+HW pages | No mixed-content source with legibility labels | 0 |
| handwriting_style | `handwriting_assessment.content_type` | HIGH | All styles per legibility level (cursive, block, mixed) | Cursive/block from IAM; no style × legibility coverage | 0 |
| ink_quality | `quality.degradations` (ink_fading) | HIGH | Normal, faded, bleed-through — direct drivers of POOR/ILLEGIBLE range | Absent from all curated HW datasets | 0 |
| document_type | `domain.document_type` | MEDIUM | >= 4 types (letter, form, note, manuscript) | Letters/notes (IAM), scene images (HierText); limited variety | 0 |
| resolution | `resolution.category` | MEDIUM | >= 3 tiers — low resolution drives legibility degradation | Scanner-sourced are 300 DPI; variation absent | 0 |

**Key diversity gaps identified before assembly**:

- **Score distribution gap (ILLEGIBLE/POOR)**: The 0.00–0.35 range is entirely absent. A
  regression model trained without anchors in this region will extrapolate wildly for low-
  legibility inputs. This is the most severe diversity failure specific to the regression task.
- **Script diversity**: CJK and Devanagari handwriting are absent from the training pool.
  Legibility criteria differ by script — Arabic diacritics affect legibility differently than
  Latin character spacing. The model cannot generalize legibility assessment across scripts
  without cross-script training signal.
- **Historical documents**: Pre-1900 manuscripts with ink fade, foxing, and deteriorated paper
  are the most natural source of ILLEGIBLE and POOR scores. Zero historical handwriting datasets
  are in the training pool. This gap simultaneously prevents coverage of the low legibility range
  and the `document_age=historical` diversity dimension.
- **Writing instrument**: Pencil handwriting (lower contrast, prone to smearing) and faded ink
  (aging) are the dominant mechanical causes of poor legibility. Neither is tracked in L2
  metadata. Without this dimension, the model cannot learn why handwriting scores low — it
  can only associate appearance with score without causal grounding.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 0 / 100 (dataset not assembled; all assessments are structural projections)

| Wild Condition | L2 Field Evidence | Status | Gap Description |
| --- | --- | --- | --- |
| Completely illegible handwriting (score ~0.00–0.10) | `handwriting_assessment.legibility_score` near 0.0 | ABSENT | No training examples; KHATT OOD provides 20+ pages for evaluation only — model will extrapolate, not learn |
| Medical prescription writing (notoriously poor legibility, small tight cursive) | No dedicated L2 field | ABSENT | No medical handwriting dataset in source pool; primary real-world source of POOR/ILLEGIBLE scores |
| Historical manuscripts with ink fade and foxing (aged/historical POOR) | `image_properties.document_age` = historical | ABSENT | No historical handwriting dataset in training pool; natural source of 0.20–0.40 score range |
| Non-native writer's handwriting in second language (structurally correct but atypical letterforms) | `language.script_code` mismatch | ABSENT | Not represented in any source dataset; common in bilingual business documents |
| Child handwriting (irregular letter sizing, inconsistent spacing) | No dedicated L2 field | ABSENT | Not represented; common in educational document processing contexts |
| Mixed-quality pages (top half EXCELLENT, bottom half POOR — fatigue/pressure drop) | `handwriting_assessment.is_mixed` | ABSENT | No training source provides within-page quality variation; model must predict page-level mean |
| Pencil handwriting (low contrast, prone to smearing) | `quality.degradations` | ABSENT | Absent from all curated HW datasets; requires explicit sourcing |
| Scripts with no Latin analog (CJK cursive, Arabic diacritics) | `language.script_code` = Hans/Arab | PARTIAL | Muharaf (Arabic) in pool but no legibility scores; CJK absent entirely |
| Camera-captured handwriting with glare or uneven illumination | `capture_method.method` = camera_smartphone | PARTIAL | COCO-Text and HierText have camera-captured scene text; not exclusively handwriting pages |
| Overwriting, strikeouts, and corrections reducing legibility | `quality.degradations` | ABSENT | Strike-throughs are a natural source of FAIR/POOR scores; absent from all current sources |
| Low-resolution scan causing diffuse blur on handwriting | `resolution.category` = low | ABSENT | Scanner sources are 300 DPI; intentionally degraded low-res handwriting absent |
| Handwriting on complex printed form backgrounds | `structure.layout_type` mixed | PARTIAL | FUNSD has form fill-ins; too small (200 pages) for meaningful training signal |
| Calligraphic handwriting (legible to experts but visually atypical) | No dedicated L2 field | ABSENT | High legibility for skilled readers but unusual letterforms; model may assign FAIR incorrectly |

**Wild condition coverage summary**: 2 partial, 11 absent, 0 fully covered.

The most critical wild condition — completely illegible handwriting — is entirely absent from
training and can only be evaluated via KHATT OOD. The model will produce arbitrary mu values
for any input at the ILLEGIBLE end of the scale, with no training signal to constrain them.
The sigma_sq output in this range will reflect Gaussian NLL optimization on VLM label noise,
not genuine uncertainty about illegibility.

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required for SIG-G4-5 | Notes |
| --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | `legibility_score` (VLM-derived per image); >= 20 images with score <= 0.10 (ILLEGIBLE) | THE primary source for ILLEGIBLE-range evaluation — critical for anchoring regression at low end; KHATT is the only identified OOD source for this range |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc) | `legibility_score` (VLM-derived), `script=HANS/HANT` | Tests cross-script generalization of legibility assessment; CJK absent from training |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | `legibility_score` (VLM-derived), `script=Deva` | Devanagari legibility criteria differ from Latin; model must generalize to novel script |
| 5d. Specialized content handwriting | 50 | Mathematical notation, engineering drawing archives | `legibility_score` (expert-rated, not VLM) | Specialized notation legibility is domain-specific; expert rating preferred over VLM for this sub-source |

### Regression-Specific OOD Notes

- **Human ratings for OOD evaluation**: To compute a meaningful Pearson r against human ratings,
  at minimum 100 OOD images must have human-collected legibility scores (3 raters, averaged).
  Without this, OOD Pearson r reflects VLM-VLM agreement, which can trivially reach 0.80 even
  for a poorly calibrated model. This is the VLM circular validation risk (see Section 8).
- **ILLEGIBLE coverage**: KHATT 5a must include >= 20 ILLEGIBLE pages. This should be increased
  to >= 50 ILLEGIBLE examples for reliable estimation of Pearson r at the low end (with only 20
  examples, the standard error on r in that sub-range exceeds 0.15).
- **Score range balance**: OOD should span the full 0–1 legibility range proportionally. If
  KHATT 5a provides mostly GOOD/EXCELLENT pages with only 20 ILLEGIBLE examples, the OOD
  Pearson r will be driven almost entirely by the well-covered GOOD/EXCELLENT range and will
  not reveal the model's failure to predict low scores.

### OOD Acquisition Status

**Status**: Not started (Phase 5, P0)

### Missing OOD Sub-sources

- Human-rated legibility scores for any OOD sub-source — currently all planned as VLM-derived
- Dedicated POOR range (0.20–0.40) OOD examples beyond what KHATT provides
- Latin-script POOR/ILLEGIBLE OOD examples (KHATT is Arabic-only; Latin-script low-legibility
  OOD is entirely absent)

### OOD Leakage Risk

**Level**: MEDIUM

KHATT, CASIA-HWDB, and IIIT-INDIC are not in the training dataset pool. Direct overlap risk
is LOW. However, if VLM is used to generate both training labels and OOD evaluation scores,
the measured Pearson r will reflect VLM self-consistency rather than model accuracy against
human perception. This is a circular evaluation risk, not a data leakage risk, but it has
the same practical effect of giving a false reading of model quality.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-2 (legibility_cls) | legibility_cls is the discretized version of legibility_reg score — they predict the same underlying quantity | Score-to-class boundaries must be applied consistently. At inference, the class from legibility_cls must match the score range from legibility_reg (e.g., if legibility_cls=GOOD, then legibility_reg mu must be in 0.55–0.80). Inconsistencies indicate multi-head calibration failure. |
| SIG-G4-1 (presence_cls) | Legibility is undefined if presence=NONE | Images with presence=NONE must have legibility_score masked from regression loss. N_A sentinel must be -1.0 (not 0.0). Failure to mask trains the model to output near-zero scores for printed pages. |
| SIG-G4-4 (presence_reg) | Shares Gaussian NLL head architecture | Both use (mu, sigma_sq). Calibration must be done independently. sigma_sq on legibility_reg is expected to be systematically larger than on presence_reg because legibility is more subjective. |
| SIG-G4-3 (content_type_cls) | Shares training dataset; content_type affects legibility perception | Cursive content_type does not imply lower legibility — but the model must not conflate them. Per-style Pearson r breakdown recommended at evaluation to verify independence. |

### Split Leakage Risk

**Level**: MEDIUM — same as all G4 heads.

Global split registry (SHA256-keyed) required. Additional regression-specific risk: if the
same image appears in both the training pool (with VLM-derived legibility score) and the OOD
evaluation pool (with human-rated score), the difference in label origin will create systematic
bias in the measured Pearson r. The train/OOD split must be verified not only for image
deduplication but also for label provenance consistency within each split.

### Label Convention

`legibility_score` is a float in [0.0, 1.0] where 0.0 = completely illegible and 1.0 = perfect
legibility equivalent to printed text. The N_A condition (no handwriting present) is represented
as a masked loss during training — sentinel value is -1.0, not 0.0.

**Mapping intent** (empirical validation required before use): EXCELLENT ~ 0.90–1.00, GOOD ~
0.60–0.80, FAIR ~ 0.40–0.55, POOR ~ 0.20–0.35, ILLEGIBLE ~ 0.05–0.15. These anchors are
provisional until calibrated against human MOS data.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| HW-LEG-REG-G01 | HW-LEG-D01 | `handwriting_assessment.legibility_score` unpopulated for all datasets — no label source exists anywhere | Labels were never annotated; regression labels require continuous scores which no existing annotation process provides | Define VLM labeling pipeline targeting 5-point MOS-like scale; run calibration study (300 human-rated images) before large-scale deployment | 1 day protocol + 3 days annotation for calibration set |
| HW-LEG-REG-G02 | HW-LEG-D02 | N_A sentinel defect — scaffold uses 0.0 but masked loss requires -1.0 | Inconsistency between the score-to-class mapping table (N_A=0.0) and the assembly specification (masked loss) | Correct sentinel to -1.0 in all assembly scripts, manifest schemas, and documentation before any training manifests are generated | 0.5 days |
| HW-LEG-REG-G03 | — | Class-to-score mapping formula not empirically validated — current linear interpolation has no human MOS anchor | No human legibility MOS study has been conducted on any training dataset | Run human rating collection on 300 images (spanning all legibility levels including ILLEGIBLE from KHATT); derive mapping empirically from MOS data | 1 day protocol + 2 days annotation |
| HW-LEG-REG-G04 | — | ILLEGIBLE range (0.00–0.20) has zero training anchors — regression head cannot learn this region | Structural curation bias: all curated HW corpora filter out unreadable images | Source or synthesize 500–1,000 images with legibility score <= 0.20 (historical archives, medical writing, or heavy augmentation of FAIR examples); shared with HW-LEG-G01 from legibility_cls | 2–3 days |
| HW-LEG-REG-G05 | — | Pearson r >= 0.80 performance target exceeds the theoretical IAA ceiling | IAA=60-70% on classification implies Pearson r ceiling ~0.60–0.65 against human ratings; target was set without IAA analysis | Revise target to Pearson r >= 0.55 (vs human ratings) or SRCC >= 0.60 (vs VLM ratings with circular validation caveat documented) | 0 days effort — governance decision |
| HW-LEG-REG-G06 | — | `handwriting` subcommand of `prepare_multitask_datasets.py` not implemented — shared P0 blocker with all G4 heads | Deprioritized during Stream 4C | Implement subcommand (shared blocker); include masked loss flag for N_A images and sentinel value -1.0 | 2 days (shared) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-LEG-REG-G07 | VLM circular validation risk — if VLM assigns training labels AND evaluates OOD images, Pearson r measures VLM-VLM agreement not model-vs-human performance | No human-rated OOD evaluation planned | Collect human ratings on >= 100 OOD images (KHATT sub-source 5a) from >= 3 raters; use these as the definitive evaluation target | 1 day |
| HW-LEG-REG-G08 | Score compression — VLM pilot showed 83% of scores compressed to 2.5–3.2 on a 5-point scale; legibility VLM will similarly compress to 0.5–0.8 range, training model unable to use full scale | Known VLM behavior from IQA pilot | Use prompt engineering to force VLM to use full scale (anchor examples at 1.0 and 5.0 in few-shot prompt); validate score distribution before large-scale labeling | 0.5 days |
| HW-LEG-REG-G09 | sigma_sq calibration undefined — Gaussian NLL head must predict uncertainty proportional to IAA, not optimize toward zero variance | No calibration protocol designed | Post-training calibration: plot predicted sigma_sq vs actual squared error on val set; apply temperature scaling if sigma_sq is systematically too low or too high | 1 day |
| HW-LEG-REG-G10 | Muharaf and PUCIT-OHUL VLM labeling not run — POOR and FAIR ranges undercovered | GCS-only datasets; labeling deferred | Run VLM legibility scoring on both datasets (~28K images total); validate VLM quality on Arabic/Urdu scripts separately from Latin calibration | 2–3 days compute |
| HW-LEG-REG-G11 | Training instability risk — Gaussian NLL with large sigma_sq may dominate Kendall uncertainty weighting and suppress mu optimization | IAA noise implies large sigma_sq is correct answer, which may cause loss to favor sigma_sq inflation | Monitor mu-SRCC and sigma_sq-calibration independently during training; add mu-reconstruction loss term if sigma_sq inflation occurs | 0.5 days monitoring setup |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| HW-LEG-REG-G12 | Derived-at-inference alternative not evaluated — legibility_reg could be computed from legibility_cls output via monotonic mapping at inference time rather than training an independent regression head | Prototype inference-time derivation; compare Pearson r against trained regression head; if equivalent, retire the independent head and derive from legibility_cls |
| HW-LEG-REG-G13 | Per-script Pearson r not planned — Arabic/CJK legibility may have systematically different score distributions | Compute Pearson r breakdowns by script_code at evaluation time |
| HW-LEG-REG-G14 | Cross-VLM agreement study not planned — if Gemini Vision is biased toward certain script styles, legibility scores inherit that bias | Run cross-VLM agreement check (Gemini vs Claude Vision on 100 images); document inter-VLM SRCC before committing to one VLM for large-scale labeling |
| HW-LEG-REG-G15 | Construct validity study not planned — verify that legibility_score as predicted by the model correlates with downstream OCR accuracy on those documents | After training, measure correlation between predicted legibility_score and OCR CER on a 500-page sample |

---

## Section 9 — Multi-Model Consensus

**Consensus Run**: 2026-02-23
**Models Consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)
**Confidence**: 9–10 / 10 (unanimous across both models)

### Analyst Pre-Consensus Summary

SIG-G4-5 (legibility_reg) inherits all three structural blockers from SIG-G4-2 (legibility_cls)
— structural data void at the ILLEGIBLE end, IAA ceiling of 60-70%, and absent L2 labels —
and adds five regression-specific validity concerns on top:

1. **Arbitrary class-to-score mapping**: Converting ordinal classes to a continuous score requires
   an empirical MOS study to calibrate anchors. The proposed linear interpolation is unsupported
   and will systematically bias the label distribution (under-estimating the ILLEGIBLE-to-POOR
   gap, which is perceptually much larger than the GOOD-to-EXCELLENT gap).

2. **Pearson r ceiling from IAA noise**: With IAA=65% on the classification task, the theoretical
   maximum Pearson r against human ratings on the derived continuous score is approximately 0.60–
   0.65. The target of r >= 0.80 exceeds this ceiling by 15–20 points — it is unachievable
   regardless of data quantity.

3. **sigma_sq semantic emptiness**: The Gaussian NLL head is designed to model genuine label
   uncertainty. Without human MOS data (which provides both mean and variance per image), sigma_sq
   will learn to fit VLM label noise rather than genuine legibility ambiguity. The output will
   appear calibrated against VLM labels but will be meaningless against human perception.

4. **VLM circular validation risk**: If VLM provides both training labels and OOD evaluation
   scores, Pearson r on OOD measures VLM self-consistency, not model accuracy. r=0.80 is
   trivially achievable VLM-to-VLM and would give a false sense of model quality.

5. **Regression adds no information over classification at IAA=65%**: Converting to regression
   does not recover information lost at the classification stage. It adds the arbitrary mapping
   assumption without providing any empirical advantage. The regression head is strictly harder
   to train, validate, and interpret than the classification head under these conditions.

### Consensus Questions and Findings

**Q1 — Class-to-score linear mapping: empirically defensible?**

Both models: **Not defensible.** Unanimous at 9–10/10 confidence.

Rationale: Ordinal class labels encode rank order, not metric distances. The perceptual distance
between ILLEGIBLE and POOR is substantially larger than between GOOD and EXCELLENT on any human
rating scale. A linear interpolation assumes equal inter-class spacing, which is false. The only
empirically defensible path is to collect human MOS data on images spanning all legibility levels
and derive the mapping from the resulting distribution.

Alternative approach (Gemini 2.5 Pro): Ordinal regression (CORAL loss) is more statistically
honest than imposing an arbitrary linear scale, because it preserves the rank-order constraint
without claiming metric distances.

**Q2 — Is Pearson r >= 0.80 achievable given IAA=60-70%?**

Both models: **No. Target is unachievable under current conditions.**

Reasoning: The reliability of a measurement instrument (in this case, human legibility judgment)
bounds the correlation any model can achieve against that instrument. With IAA=65%, the expected
Pearson r between two independent human raters is approximately sqrt(0.65) ≈ 0.81 at best — but
only for the same measurement instrument. A model predicting from image features faces additional
error sources, placing a realistic ceiling at Pearson r ≈ 0.60–0.65 against human ratings.

The Pearson r >= 0.80 target assumes human-level agreement, which is not achievable for a
subjective perceptual task with 60-70% IAA. Both models recommend revising to SRCC >= 0.55
or Pearson r >= 0.55 against human ratings, with the caveat that VLM-based evaluation must
be separately tracked as a secondary metric.

**Q3 — Does sigma_sq adequately model label noise when labels are VLM-derived?**

Both models: **No. sigma_sq without MOS ground truth is semantically empty.**

Reasoning (Gemini 2.5 Pro, 10/10 confidence): The industry standard for subjective quality
assessment is Mean Opinion Score (MOS) from multiple human raters. MOS provides both the
regression target (mean score) and ground truth uncertainty (variance across raters). Training
sigma_sq without this data means the head learns to fit the VLM label distribution, not genuine
legibility ambiguity. The resulting sigma_sq values will appear calibrated against VLM labels
but will be misleading for downstream consumers who expect them to reflect human-perceptual
uncertainty.

The correct approach: collect >= 3 human ratings per training image on a 500-image calibration
set, use the rating variance as sigma_sq ground truth, and train sigma_sq to predict rating
disagreement. This transforms the Gaussian NLL head from an arbitrary uncertainty estimate into
a meaningful inter-rater uncertainty predictor.

**Q4 — Is the task validity concern a Blocked-level issue?**

Both models: **Yes. BLOCKED.**

Gemini 2.5 Pro (10/10): "The proposal is fundamentally unsound. It attempts to build a high-
precision regression model on a foundation of low-quality, low-granularity, and incomplete data.
Shipping this head would create significant technical debt. Its sigma_sq output would be
dangerously misleading."

Key finding (both models): Shipping this head with VLM-derived labels and the proposed linear
mapping creates a false sense of precision. Downstream consumers of the legibility_score will
treat it as a reliable continuous signal when it is actually an arbitrary ordinal encoding
with calibrated-appearing uncertainty that is not grounded in human perception.

**Q5 — Top risks not in the gap registry**

Risks identified by consensus not present in the scaffold:

1. **VLM circular validation** (Gemini 2.5 Pro, HIGH): If VLM assigns training labels and
   evaluates OOD images, Pearson r measures VLM self-consistency not model quality. r=0.80
   is trivially achievable VLM-to-VLM and is meaningless as a performance target.

2. **Score compression** (derived from IQA VLM pilot data, HIGH): The IQA VLM pilot showed
   83% of scores in a 0.5-range on a 5-point scale. VLM legibility scoring will similarly
   compress to 0.5–0.8 on the 0-1 scale, making the model unable to learn to predict extreme
   values and systematically underestimating the ILLEGIBLE and EXCELLENT extremes.

3. **Training instability from sigma_sq inflation** (HIGH): With high IAA noise, the correct
   Gaussian NLL solution is large sigma_sq across all samples. Kendall uncertainty weighting
   may assign low weight to the legibility_reg head as sigma_sq inflates, causing mu to
   receive insufficient gradient signal during multi-task training.

4. **Regression adds no information over classification** (MEDIUM): At IAA=65%, the
   legibility_cls head achieves Macro F1 ~0.60. The legibility_reg head does not recover
   information lost at the classification stage — it adds the arbitrary mapping assumption
   without empirical advantage. The derived-at-inference alternative (compute legibility_score
   from legibility_cls output via monotonic mapping) may be equivalent or superior.

5. **N_A=0.0 sentinel latent defect** (HIGH): The scaffold table uses N_A=0.0, which if
   propagated to assembly scripts would train the model to predict near-zero scores for printed
   pages. This must be caught and corrected before any manifest generation.

**Q6 — Minimum changes to move from Blocked to Needs Work**

Both models agreed on the minimum remediation set:

1. Collect human MOS ratings on >= 300 images (spanning ILLEGIBLE through EXCELLENT, including
   KHATT ILLEGIBLE examples), >= 3 raters per image. This establishes (a) empirical mapping
   anchors, (b) a realistic Pearson r ceiling, and (c) ground truth for sigma_sq calibration.
2. Revise performance target from Pearson r >= 0.80 to Pearson r >= 0.55 (vs human ratings),
   with VLM-based SRCC reported as a secondary metric with circular validation caveat.
3. Correct N_A sentinel to -1.0 (masked loss) in all schemas and documentation.
4. Prototype the derived-at-inference alternative: compute legibility_score from legibility_cls
   output via monotonic mapping. If Pearson r is equivalent, retire the independent regression
   head and derive at inference time, eliminating the need for continuous label collection.

### Consensus Summary

| Question | Gemini 2.5 Pro | Gemini 3 Pro Preview | Consensus |
| --- | --- | --- | --- |
| Class-to-score linear mapping | Not defensible; ordinal regression better | Not defensible; MOS collection required | Not defensible — empirical MOS mapping required |
| Pearson r >= 0.80 achievable? | No — ceiling ~0.60–0.65 | No — ceiling from IAA noise | No — revised target Pearson r >= 0.55 |
| sigma_sq with VLM labels | Semantically empty; MOS required | MOS variance as sigma_sq GT required | sigma_sq requires MOS ground truth |
| Task validity concern | BLOCKED | BLOCKED | BLOCKED |
| Overall rating | BLOCKED (10/10 confidence) | BLOCKED (9/10 confidence) | BLOCKED (unanimous) |

### Scoring Summary

| Component | Weight | Score | Weighted | Notes |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 8 / 100 | 2.8 | No legibility_score labels anywhere; ILLEGIBLE range = 0; scoring is strictly worse than legibility_cls because regression requires continuous labels not derivable from existing annotations |
| 14-Dimension Coverage | 25% | 0 / 100 | 0.0 | Dataset not assembled; score_distribution dimension fatally uncovered (0.00–0.35 absent); all 14 dimensions score 0 |
| Wild Condition Coverage | 20% | 3 / 100 | 0.6 | 2 conditions partially covered (Arabic via Muharaf without scores, camera-captured scene text); 11 conditions entirely absent; ILLEGIBLE wild condition absent from training |
| OOD Design Quality | 20% | 55 / 100 | 11.0 | OOD plan is structurally sound; KHATT ILLEGIBLE coverage reduces deduction; deducted for: absent human ratings for OOD evaluation, VLM circular validation risk, Latin-script POOR/ILLEGIBLE OOD absent |
| **Overall** | 100% | — | **14.4** | Grade: Blocked |

**Grade**: Blocked — score 14.4/100. Lower than SIG-G4-2 (legibility_cls, 20.8/100) because
regression-specific validity concerns add to the identical underlying data blockers.

**Top Recommendations (consensus-derived)**:

1. **Immediate governance**: Revise performance target from Pearson r >= 0.80 to Pearson r >= 0.55
   (vs human ratings). Document that VLM-based Pearson r is a secondary metric with circular
   validation caveat. Do not evaluate against VLM-only OOD scores as primary signal.

2. **Prototype derived-at-inference alternative**: Before investing in continuous label collection,
   prototype computing legibility_score from legibility_cls probabilities via monotonic mapping
   (e.g., expected value under class-to-score mapping). If this achieves Pearson r within 0.05 of
   the trained regression head, retire SIG-G4-5 as an independent head and derive at inference time.

3. **Correct N_A sentinel immediately**: Change N_A sentinel from 0.0 to -1.0 (masked loss) in
   all schemas, documentation, and future assembly scripts before any manifest generation occurs.

4. **Human MOS collection as gating requirement**: Collect >= 300 human-rated legibility scores
   (>= 3 raters per image, KHATT ILLEGIBLE subset included) before large-scale VLM labeling.
   Use MOS variance as sigma_sq ground truth targets and use MOS distribution to calibrate
   class-to-score mapping empirically.

5. **Resolve SIG-G4-2 blockers first**: SIG-G4-5 shares all P0 blockers with SIG-G4-2
   (ILLEGIBLE training examples, VLM labeling pipeline, assembly subcommand). No regression-
   specific work should begin until SIG-G4-2 is at least at "Needs Work" status.
