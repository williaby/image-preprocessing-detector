# Head Adequacy Review: legibility_reg (SIG-G4-5)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: E — Handwriting
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | SIG-G4-5 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | legibility_reg (also written as handwriting_legibility_score) |
| Task Type | Regression — 0-1 continuous (quality score: 0 = illegible, 1 = perfect) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P1 |
| Performance Target | SRCC ≥ 0.65 vs human legibility ratings |
| Primary L2 Field | `handwriting_assessment.legibility_score` (float 0-1) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5); SIG-G4-2 (legibility_cls is the discretized version of this score) |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.legibility_score` _(float 0.0–1.0; 0 = illegible, 1 = perfect legibility)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_1_annotation preferred; VLM-derived scores are the primary method for most datasets; COCO-Text provides a 3-class proxy

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Label Derivation Hierarchy

| Method | Datasets | Precision | Confidence |
| --- | --- | --- | --- |
| Direct human legibility ratings (IAA measured) | _(none identified — analysis required)_ | High | tier_0_exact |
| VLM legibility scoring (per image, 0.0–1.0) | Muharaf, PUCIT-OHUL, HierText | Medium (±0.10) | tier_1_annotation |
| 3-class proxy mapping (COCO-Text) | COCO-Text | Low (coarse discretization) | tier_2_heuristic |
| Corpus-level assignment | IAM (→ ~0.90–1.00), NIST-SD2 (→ ~0.85–0.95), DocLayNet (→ N/A) | Low (fixed range) | tier_2_heuristic |

### Score-to-Class Mapping

| Score Range | Legibility Class (SIG-G4-2) | Description |
| --- | --- | --- |
| 0.00–0.10 | ILLEGIBLE | Cannot be read |
| 0.10–0.30 | POOR | Very difficult to read |
| 0.30–0.55 | FAIR | Readable with effort |
| 0.55–0.80 | GOOD | Clearly readable |
| 0.80–1.00 | EXCELLENT | Near-print legibility |
| N/A | N/A | No handwriting present |

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| COCO-Text | 63,686 | _(legibility field: clear/blurred/others — proxy only)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| IAM | _(analysis required)_ | _(fixed high range ~0.90–1.00 by design)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| HierText | 8,281 | _(analysis required — VLM labeling required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Muharaf | _(analysis required — GCS-only locally)_ | _(no legibility annotations — VLM required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| PUCIT-OHUL | _(analysis required — GCS-only locally)_ | _(no legibility annotations — VLM required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Nepali Handwritten | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| NIST SD-19 | _(analysis required)_ | _(fixed high range ~0.85–0.95 by design)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| FUNSD | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 102,000+ images (shared with all G4 heads)
- **Gap**: No dataset has direct human legibility ratings as ground truth. Low-score range (0.0–0.30) severely undercovered — ILLEGIBLE and POOR examples are rare in available corpora. IAM skews entirely to EXCELLENT (0.90–1.00).

### VLM Validation Sampling Tier

_(analysis required — VLM scoring is the primary label method; VLM calibration against human ratings (SRCC target 0.65) must be validated on a held-out human-rated sample before large-scale labeling)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-05-A | No dataset has direct human legibility ratings — VLM is the best available method but introduces model-in-the-loop bias | HIGH — SRCC target of 0.65 measured against VLM scores, not human ground truth |
| KI-G4-05-B | ILLEGIBLE and POOR score range (0.0–0.30) severely undercovered in training corpora | HIGH — model cannot reliably score very low legibility without training signal |
| KI-G4-05-C | IAM contributes only EXCELLENT-range scores (0.90–1.00) — training will skew to high end | HIGH — may cause regression to predict high scores for all handwriting |
| KI-G4-05-D | Muharaf and PUCIT-OHUL have no legibility annotations — largest potential sources for mid-to-low scores require full VLM labeling | HIGH — significant compute cost; GCS-only locally |
| KI-G4-05-E | COCO-Text 3-class proxy (clear/blurred/others) has large within-class score variance — mapping to continuous 0-1 is imprecise | MEDIUM — systematic quantization noise in labels |

### Remediation Path

_(analysis required — initial steps: 1) VLM calibration study on 100 human-rated images, 2) VLM labeling pipeline for Muharaf/PUCIT-OHUL, 3) assess whether SRCC target of 0.65 is achievable given label quality constraints)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 102,000+ images (shared with all G4 heads) |
| Assembly Status | ⏳ Not started |
| Current Count | _(analysis required)_ |
| Gold Standard | Human legibility ratings (none identified); VLM scores as primary proxy |
| Performance Target | SRCC ≥ 0.65 vs human legibility ratings (requires human rating collection for final evaluation) |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Score Distribution Requirements

| Score Range | Legibility Class | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- | --- |
| 0.00–0.10 | ILLEGIBLE | ≥ 2% | KHATT (OOD only) | CRITICAL — absent from training |
| 0.10–0.30 | POOR | ≥ 5% | Muharaf, PUCIT-OHUL (VLM) | HIGH — requires VLM labeling |
| 0.30–0.55 | FAIR | ≥ 15% | COCO-Text (blurred), Muharaf, PUCIT-OHUL | HIGH — requires VLM labeling |
| 0.55–0.80 | GOOD | ≥ 30% | COCO-Text (clear), HierText (VLM) | MEDIUM |
| 0.80–1.00 | EXCELLENT | ≥ 40% | IAM, NIST-SD2, FUNSD | LOW — well-covered |
| N/A | N/A | Set by NONE presence | Printed negatives | N/A — excluded from regression loss |

**Blockers**:

- handwriting subcommand of `prepare_multitask_datasets.py` not yet implemented
- VLM legibility labeling pipeline for Muharaf and PUCIT-OHUL not yet run
- Human rating collection for final SRCC evaluation not planned
- ILLEGIBLE range (0.0–0.10) entirely absent from training — decision required

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL | ≥ 3 methods (born_digital, scanner, camera) | unknown | TBD |
| domain | `domain.level1` | HIGH | ≥ 5 domains | unknown | TBD |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages (modern, aged, historical) | unknown | TBD |
| script_code | `language.script_code` | HIGH | ≥ 4 scripts (LATN, ARAB, DEVA, JPAN) | unknown | TBD |
| resolution | `resolution.category` | HIGH | ≥ 3 tiers (legibility correlates with resolution) | unknown | TBD |
| layout_type | `structure.layout_type` | LOW | ≥ 3 types | unknown | TBD |
| degradation | `quality.degradations` | CRITICAL | ≥ 4 types (blur, noise, bleed-through, ink_fading all affect legibility) | unknown | TBD |
| legibility_score_range | `handwriting_assessment.legibility_score` | CRITICAL | Full 0–1 range with density in 0.10–0.80 | unknown | TBD |
| writing_instrument | _(no dedicated L2 field)_ | HIGH | Pen, pencil, marker (affects legibility independently of content) | unknown | TBD |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | unknown | TBD |
| ink_quality | `quality.degradations` (ink_fading) | HIGH | Normal, faded, bleed-through | unknown | TBD |
| mixed_content | `handwriting_assessment.is_mixed` | MEDIUM | Both pure and mixed pages | unknown | TBD |
| background_complexity | `image_properties.background` | HIGH | Plain and complex (background affects legibility perception) | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Pencil handwriting (inherently lower contrast) | `quality.degradations` | ⏳ | analysis required |
| Faded ink (aged documents) | `quality.degradations` incl. ink_fading | ⏳ | analysis required |
| Bleed-through reducing legibility | `quality.degradations` incl. bleed_through | ⏳ | analysis required |
| Camera glare obscuring text | `capture_method.method` = camera_smartphone | ⏳ | analysis required |
| Low-resolution scan causing blur | `resolution.dpi` ≤ 150 | ⏳ | analysis required |
| Dense cursive in unfamiliar script | `language.script_code` non-LATN + `handwriting_assessment.content_type` = cursive | ⏳ | analysis required |
| Overwriting and corrections on same page | `quality.degradations` | ⏳ | analysis required |
| Historical letterforms (pre-1900 style) | `image_properties.document_age` = historical | ⏳ | analysis required |
| Handwriting under watermark or stamp | `quality.degradations` | ⏳ | analysis required |
| Completely illegible handwriting (0.0 score) | `handwriting_assessment.legibility_score` = 0.0 | ⏳ | absent from training; OOD-only (KHATT) |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | legibility_score (VLM-derived per image), ≥ 20 images with legibility_score ≈ 0.0–0.05 (ILLEGIBLE) | SigLIP 2 | THE primary source for ILLEGIBLE range evaluation — critical for SIG-G4-5 regression at low scores |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc if access denied) | legibility_score (VLM-derived per image), script=HANS/HANT | SigLIP 2 | CJK legibility assessment tests generalization beyond Latin script |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | legibility_score (VLM-derived per image), script=Deva | SigLIP 2 | Devanagari legibility stress |
| 5d. Specialized content handwriting | 50 | Internal collection / TBD | legibility_score (expert-rated), content_type=specialized | SigLIP 2 | Specialized notation legibility is domain-specific — human expert rating preferred over VLM |

### Additional Regression-Specific OOD Notes

For reliable SRCC computation, OOD legibility scores should be verified against human ratings where possible (at least 100-image human-rated subset). VLM-only labels for OOD will give noisy SRCC estimates. KHATT ILLEGIBLE images are the most critical OOD subset for this head — failure to cover 0.0–0.10 range in evaluation is a significant blind spot.

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 5, P0)

### Missing OOD Sub-sources

- Human-rated legibility scores for OOD evaluation (any size sample) — currently no ground truth beyond VLM
- Additional POOR/FAIR range OOD examples beyond what KHATT provides

### OOD Leakage Risk

**Level**: MEDIUM

Same as all G4 heads. VLM-labeled OOD scores may circularly reflect VLM training biases — if VLM is also used for training labels, OOD SRCC will be overestimated relative to true human performance. Recommend collecting at minimum 100 human-rated images for final SRCC validation.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-2 (legibility_cls) | legibility_cls is the discretized version of legibility_reg score | Score-to-class boundaries must be applied consistently (see score-to-class mapping table in Section 2). Same image must have logically consistent legibility_score and legibility class. |
| SIG-G4-1 (presence_cls) | Legibility is meaningless if presence=NONE | Images with presence=NONE must have legibility_score excluded from regression loss (masked); label value set to -1 or special sentinel |
| SIG-G4-4 (presence_reg) | Shares Gaussian NLL head architecture | Both reg heads use (mu, sigma_sq) output; calibration must be done independently. Presence_reg and legibility_reg are co-trained but independently evaluated. |

### Split Leakage Risk

**Level**: MEDIUM

Same as all G4 heads — global split registry required. Additional risk: if VLM is used for both training labels and OOD evaluation scoring, SRCC will reflect VLM-VLM agreement rather than VLM-human agreement. This is a known limitation that must be documented in the model card.

### Label Convention

legibility_score is a float in [0.0, 1.0] where 0.0 means completely illegible and 1.0 means perfect legibility equivalent to printed text. The N/A condition (no handwriting present) is represented as a masked loss during training — the output value on N/A images is not used. COCO-Text mapping: clear → [0.70, 0.95] (VLM narrows), blurred → [0.25, 0.55] (VLM narrows), others → VLM per-image. IAM → fixed [0.90, 1.00]. NIST-SD2 → fixed [0.85, 0.95].

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G4LR-G01 | — | handwriting subcommand of prepare_multitask_datasets.py not implemented | Phase 3 dataset prep deprioritized | Implement subcommand (shared blocker with all G4 heads) | 2 days (shared) |
| G4LR-G02 | — | No ground truth human legibility ratings exist for any training or OOD dataset | Annotation not collected during dataset assembly | Collect human ratings on ≥ 100 images for calibration; define rating protocol before VLM labeling begins | 1 day protocol + 3 days annotation |
| G4LR-G03 | — | ILLEGIBLE score range (0.0–0.10) entirely absent from training data | No training corpus contains pages confirmed illegible to human readers | Decide: source ~200 ILLEGIBLE training examples OR accept as open-set and target SRCC on 0.10–1.00 sub-range only | 0.5 days decision |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G4LR-G04 | VLM legibility labeling pipeline not yet run for Muharaf and PUCIT-OHUL — POOR/FAIR range undercovered | GCS-only datasets; labeling deferred | Run VLM legibility scoring on these datasets (Gemini Vision or similar); budget ~2-3 days compute | 2–3 days compute |
| G4LR-G05 | IAM corpus-level label (0.90–1.00) does not reflect within-corpus legibility variance | IAM is a quality-controlled corpus; individual pages vary | Run per-image VLM scoring on IAM subset to capture within-corpus variance; or reduce IAM weight in training | 1 day |
| G4LR-G06 | SRCC target of 0.65 is measured against VLM scores in absence of human ratings — target may be unreachable by current measurement method | No human rating ground truth | After collecting 100 human-rated calibration set, re-assess whether 0.65 SRCC vs humans is achievable | 0.5 days (after G4LR-G02) |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G4LR-G07 | Gaussian NLL calibration not planned — sigma_sq may be miscalibrated (overconfident or underconfident) | Add calibration step post-training: plot predicted sigma_sq vs actual error on val set |
| G4LR-G08 | Regression head may not generalize to non-Latin scripts if training skews Latin (IAM dominant) | Audit per-script SRCC breakdown; add ARAB/DEVA per-script evaluation slice |
| G4LR-G09 | VLM labeling bias documentation not planned — if Gemini Vision is biased toward certain script styles, legibility scores will inherit that bias | Run cross-VLM agreement check (Gemini vs Claude Vision on 100 images); document inter-VLM agreement |

---

## Section 9 — Multi-Model Consensus

**Status**: ⏳ Pending execution

**Adequacy Rating (pre-consensus)**: ⏳ TBD (analysis required)

**Analyst Summary**: _(To be written after Sections 2–8 analysis is complete)_

**Consensus Prompt**: _(To be written after Section 8 gap registry is complete)_

**Models**: google/gemini-2.5-pro, google/gemini-3-pro-preview, openai/gpt-5.2,
deepseek/deepseek-r1-0528, x-ai/grok-4 (all neutral)

**Consensus Summary**: _(Pending)_

**Final Rating**: _(Pending)_

**Top Recommendations**: _(Pending)_

### Scoring Summary

| Component | Weight | Score | Weighted |
| --- | --- | --- | --- |
| Source Pool Adequacy | 35% | TBD | TBD |
| 14-Dimension Coverage | 25% | TBD | TBD |
| Wild Condition Coverage | 20% | TBD | TBD |
| OOD Design Quality | 20% | TBD | TBD |
| **Overall** | 100% | — | TBD |

**Grade**: ⏳ TBD
