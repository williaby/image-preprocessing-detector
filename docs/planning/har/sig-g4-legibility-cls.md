# Head Adequacy Review: legibility_cls (SIG-G4-2)

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
| Head ID | SIG-G4-2 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | legibility_cls (also written as handwriting_legibility_cls) |
| Task Type | Classification — 6 classes (N/A / POOR / FAIR / GOOD / EXCELLENT / ILLEGIBLE) |
| Output Format | Softmax over 6 legibility levels |
| Priority | P1 |
| Performance Target | Accuracy ≥ 85% |
| Primary L2 Field | `handwriting_assessment.legibility` (6-class enum) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5) — all trained on the same dataset |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.legibility` _(6-class enum: N/A / POOR / FAIR / GOOD / EXCELLENT / ILLEGIBLE)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact or tier_1_annotation preferred; VLM labeling likely required for POOR/FAIR/GOOD distinctions

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Class Definitions

| Class | Description |
| --- | --- |
| N/A | No handwriting present (NONE presence level) — legibility assessment not applicable |
| POOR | Handwriting is very difficult to read; transcription requires significant effort |
| FAIR | Handwriting is readable with moderate effort |
| GOOD | Handwriting is clearly readable with minimal effort |
| EXCELLENT | Handwriting is highly legible; near-print quality |
| ILLEGIBLE | Handwriting cannot be read by a human expert |

### Critical Gap: ILLEGIBLE Class

**ILLEGIBLE is absent from all training datasets.** This class is sourced exclusively from OOD-Handwriting sub-source 5a (KHATT Arabic cursive, ≥ 20 ILLEGIBLE pages). The model will not have training signal for this class — it is an open-set test class for this head.

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| HierText | 8,281 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| COCO-Text | 63,686 | _(legibility field exists: clear/blurred/others)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| IAM | _(analysis required)_ | _(analysis required — all legible by design)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Muharaf | _(analysis required — GCS-only locally)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| PUCIT-OHUL | _(analysis required — GCS-only locally)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Nepali Handwritten | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| NIST SD-19 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| FUNSD | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 102,000+ images (shared with all G4 heads)
- **Gap**: ILLEGIBLE class entirely absent; POOR/FAIR/GOOD distinctions require per-image VLM scoring for most datasets

### VLM Validation Sampling Tier

_(analysis required — POOR/FAIR boundary especially subjective; likely Tier 2 for most handwriting datasets; Tier 3 for Muharaf/PUCIT-OHUL which have no existing legibility annotations)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-02-A | ILLEGIBLE class absent from all training datasets — only covered in OOD | HIGH — model cannot be evaluated on ILLEGIBLE in-distribution; open-set behavior only |
| KI-G4-02-B | COCO-Text legibility field uses 3-class schema (clear/blurred/others) — not directly mappable to 6-class schema | HIGH — mapping required: clear→GOOD/EXCELLENT, blurred→POOR/FAIR, others→TBD |
| KI-G4-02-C | IAM dataset labels all pages as EXCELLENT by design (clean handwriting corpus) — no coverage of lower legibility levels | MEDIUM — IAM contributes only to GOOD/EXCELLENT classes |
| KI-G4-02-D | Muharaf and PUCIT-OHUL have no legibility annotations — require VLM labeling | HIGH — significant VLM compute cost for GCS-only datasets |

### Remediation Path

_(analysis required — initial steps: 1) map COCO-Text 3-class to 6-class schema, 2) run VLM legibility labeling on Muharaf/PUCIT-OHUL, 3) confirm ILLEGIBLE-only-OOD decision with model consensus)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 102,000+ images (shared with all G4 heads) |
| Assembly Status | ⏳ Not started (blocked on label harmonization and VLM legibility labeling) |
| Current Count | _(analysis required)_ |
| ILLEGIBLE Class | OOD-only — intentionally absent from training; open-set behavior expected |
| N/A Class | All NONE-presence images receive N/A — label dependency on SIG-G4-1 |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Class Distribution Requirements

| Class | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- |
| N/A | Set by NONE-presence count | Printed negatives (DocLayNet, TableBank, RVL-CDIP) | LOW |
| POOR | ≥ 5% of handwriting images | Muharaf, PUCIT-OHUL (VLM-labeled) | HIGH — requires VLM labeling |
| FAIR | ≥ 15% of handwriting images | COCO-Text (blurred), Muharaf, PUCIT-OHUL | HIGH — requires VLM labeling |
| GOOD | ≥ 30% of handwriting images | COCO-Text (clear), HierText, IAM | MEDIUM |
| EXCELLENT | ≥ 40% of handwriting images | IAM, NIST-SD2, FUNSD | LOW |
| ILLEGIBLE | 0 (OOD only) | KHATT (OOD only) | CRITICAL — open-set gap |

**Blockers**:

- handwriting subcommand of `prepare_multitask_datasets.py` not yet implemented
- COCO-Text 3-class to 6-class legibility mapping not yet defined
- VLM legibility labeling for Muharaf and PUCIT-OHUL not yet run
- ILLEGIBLE class training strategy requires explicit model-level decision (accept as open-set vs. source training examples)

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
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers | unknown | TBD |
| layout_type | `structure.layout_type` | LOW | ≥ 3 types | unknown | TBD |
| degradation | `quality.degradations` | HIGH | ≥ 3 types (blur, noise, bleed-through relevant to legibility) | unknown | TBD |
| handwriting_style | `handwriting_assessment.content_type` | HIGH | All styles represented per legibility level | unknown | TBD |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | unknown | TBD |
| ink_quality | `quality.degradations` (ink_fading) | HIGH | Normal, faded, bleed-through represented | unknown | TBD |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | unknown | TBD |
| mixed_content | `handwriting_assessment.is_mixed` | MEDIUM | Both pure and mixed pages | unknown | TBD |
| background_complexity | `image_properties.background` | MEDIUM | Plain and complex (affects legibility perception) | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Faded ink (aged documents) | `quality.degradations` incl. ink_fading | ⏳ | analysis required |
| Bleed-through reducing legibility | `quality.degradations` incl. bleed_through | ⏳ | analysis required |
| Camera-captured handwriting (glare, uneven lighting) | `capture_method.method` = camera_smartphone | ⏳ | analysis required |
| Dense cursive script (connected letterforms) | `handwriting_assessment.content_type` = cursive | ⏳ | analysis required |
| Historical letterforms (pre-1900 script conventions) | `image_properties.document_age` = historical | ⏳ | analysis required |
| Non-Latin cursive scripts (Arabic, Devanagari) | `language.script_code` | ⏳ | analysis required |
| Overwriting / corrections on handwritten pages | `quality.degradations` | ⏳ | analysis required |
| Low-contrast handwriting (pencil, light ink) | `quality.degradations` | ⏳ | analysis required |
| Handwriting on complex printed backgrounds (forms) | `structure.layout_type` | ⏳ | analysis required |
| ILLEGIBLE handwriting (cannot be read) | `handwriting_assessment.legibility` = ILLEGIBLE | ⏳ | entirely absent from training; OOD-only |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | handwriting_presence=SUBSTANTIAL, script=Arab, text_direction=rtl | SigLIP 2 | Specifically includes ≥ 20 ILLEGIBLE pages — this is the only source of ILLEGIBLE-class evaluation data for SIG-G4-2 |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc if access denied) | handwriting_presence=DOMINANT, script=HANS/HANT | SigLIP 2 | 2–4 week access request for CASIA |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | handwriting_presence=DOMINANT, script=Deva | SigLIP 2 | Non-Latin script legibility stress |
| 5d. Specialized content handwriting | 50 | Internal collection / TBD | content_type=specialized (math notation, engineering drawings) | SigLIP 2 | Specialized content may present unique legibility challenges |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 5, P0)

### Missing OOD Sub-sources

- Additional ILLEGIBLE examples beyond KHATT 20 pages — may need supplementary source if KHATT ILLEGIBLE count is insufficient for statistical evaluation
- POOR legibility examples in non-Arabic scripts — current OOD skews toward KHATT Arabic

### OOD Leakage Risk

**Level**: MEDIUM

KHATT is not in the training dataset pool. ILLEGIBLE class in OOD is intentionally absent from training (open-set scenario). This is expected behavior for SIG-G4-2. Risk arises if KHATT images were inadvertently included in any training negative pool — SHA256 dedup required against all training sources.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-1 (presence_cls) | Shares training dataset; N/A legibility applies to NONE presence | All images with presence=NONE must have legibility=N/A; enforced during assembly |
| SIG-G4-5 (legibility_reg) | Legibility_cls is the discretized version of legibility_reg output | Class boundaries must align with score midpoint mapping (POOR: 0–0.25, FAIR: 0.25–0.50, GOOD: 0.50–0.75, EXCELLENT: 0.75–1.00, ILLEGIBLE: special sentinel) |
| SIG-G4-3 (content_type_cls) | Shares training dataset | Content type labels must be consistent on same images; both N/A when presence=NONE |

### Split Leakage Risk

**Level**: MEDIUM

Same as all G4 heads — global split registry required. Additionally, the COCO-Text legibility field creates a specific risk: COCO-Text images with existing legibility annotations may be split differently than expected if the legacy legibility field is used to stratify splits. Stratification must use image SHA256, not legacy label values.

### Label Convention

6-class enum using: N/A, POOR, FAIR, GOOD, EXCELLENT, ILLEGIBLE. The N/A value uses slash (not underscore) to distinguish from the NOT_APPLICABLE convention used in other heads. COCO-Text mapping: clear→GOOD or EXCELLENT (resolved by VLM), blurred→POOR or FAIR (resolved by VLM), others→requires case-by-case VLM assessment.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G4L-G01 | — | handwriting subcommand of prepare_multitask_datasets.py not implemented | Phase 3 dataset prep deprioritized | Implement subcommand (shared blocker with all G4 heads) | 2 days (shared) |
| G4L-G02 | — | ILLEGIBLE class absent from all training data — explicit decision required | No training corpus contains illegible handwriting pages | Decide: accept as open-set (recommended) OR source ~500 ILLEGIBLE training examples; document decision | 0.5 days decision |
| G4L-G03 | — | COCO-Text 3-class legibility schema not mapped to 6-class target schema | Different annotation systems | Define mapping rules; implement in harmonize script; run VLM on ambiguous "others" subset | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G4L-G04 | Muharaf and PUCIT-OHUL have no legibility annotations — POOR/FAIR classes undercovered without VLM labeling | Datasets collected without legibility scoring | Run VLM legibility labeling on these datasets (Gemini Vision or similar) | 2–3 days compute |
| G4L-G05 | KHATT ≥ 20 ILLEGIBLE pages is the only ILLEGIBLE evaluation source — sample size may be too small for reliable evaluation | Limited OOD budget | If KHATT provides fewer than 20 confirmed ILLEGIBLE pages, source additional ILLEGIBLE examples | 1 day |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G4L-G06 | POOR class underrepresented in Latin-script training data (IAM skews EXCELLENT) | Source degraded historical handwriting or synthetic ink-fading augmentation |
| G4L-G07 | Legibility IAA (inter-annotator agreement) not measured — subjective class boundaries | Run double-annotation on 200 sample images to measure IAA; adjust class definitions if needed |

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
