# Head Adequacy Review: presence_cls (SIG-G4-1)

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
| Head ID | SIG-G4-1 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | presence_cls (also written as handwriting_presence_cls) |
| Task Type | Classification — 5 classes (NONE / SPARSE / MODERATE / SUBSTANTIAL / DOMINANT) |
| Output Format | Softmax over 5 presence levels |
| Priority | P1 |
| Performance Target | Accuracy ≥ 88% |
| Primary L2 Field | `handwriting_assessment.presence` (5-class enum) |
| Shared-Data Heads | All G4 heads (SIG-G4-2 through SIG-G4-5) — all trained on the same dataset |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.presence` _(5-class enum: NONE / SPARSE / MODERATE / SUBSTANTIAL / DOMINANT)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact or tier_1_annotation preferred

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Class Definitions

| Class | Description |
| --- | --- |
| NONE | < 1% of page area is handwritten |
| SPARSE | 1–10% of page area is handwritten |
| MODERATE | 10–30% of page area is handwritten |
| SUBSTANTIAL | 30–60% of page area is handwritten |
| DOMINANT | > 60% of page area is handwritten |

### Label Harmonization Strategy

Labels are derived via three strategies applied per dataset:

- **all_handwritten**: IAM, NIST-SD2 — all pages labeled DOMINANT by design
- **model_derived**: HierText, COCO-Text — presence computed from polygon area ratio
- **all_printed**: DocLayNet, TableBank, RVL-CDIP — all pages labeled NONE (negatives)

`scripts/harmonize_handwriting_labels.py` is implemented (dry-run complete: 38,967 records, 9,289 positive).

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| HierText | 8,281 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| COCO-Text | 63,686 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| IAM | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Muharaf | _(analysis required — GCS-only locally)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| PUCIT-OHUL | _(analysis required — GCS-only locally)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Nepali Handwritten | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| NIST SD-19 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| FUNSD | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| DocLayNet (negatives) | 81,000 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| TableBank (negatives) | 278,000 | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| RVL-CDIP (negatives) | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 102,000+ images
- **Gap**: Dry-run shows 38,967 records (9,289 positive); short of 40K target because Muharaf and PUCIT-OHUL are GCS-only locally

### VLM Validation Sampling Tier

_(analysis required — MODERATE and SUBSTANTIAL classes likely Tier 2/3 due to subjectivity of boundary between levels)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-01 | Muharaf and PUCIT-OHUL are GCS-only locally — full run of harmonize script requires GCS access or VM | HIGH — short of 40K positive target without these datasets |
| KI-G4-02 | NONE class will be vastly over-represented from printed document negatives — class imbalance risk | HIGH — sampling cap or class weights required |
| KI-G4-03 | SPARSE class (1–10% area) is difficult to annotate accurately from model_derived strategy | MEDIUM — boundary precision affects adjacent class accuracy |
| KI-G4-04 | handwriting subcommand of prepare_multitask_datasets.py not yet implemented | HIGH — blocking full assembly |

### Remediation Path

_(analysis required — initial steps: 1) implement handwriting subcommand, 2) run full harmonize on GCS VM, 3) audit class balance and apply sampling caps)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 102,000+ images |
| Assembly Status | ⏳ Not started (label harmonization script created but full run pending) |
| Current Count | 38,967 records (dry-run estimate); target not met pending GCS-only datasets |
| Label Strategy | all_handwritten (IAM/NIST-SD2) + model_derived (HierText/COCO-Text) + all_printed (negatives) |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Class Distribution Requirements

| Class | Target % | Derivation Method | Risk |
| --- | --- | --- | --- |
| NONE | Capped (negatives abundant) | all_printed | LOW — over-representation risk |
| SPARSE | ≥ 10% of positives | model_derived | MEDIUM — boundary precision |
| MODERATE | ≥ 20% of positives | model_derived | MEDIUM |
| SUBSTANTIAL | ≥ 30% of positives | model_derived + all_handwritten | MEDIUM |
| DOMINANT | ≥ 30% of positives | all_handwritten | LOW — IAM/NIST-SD2 fully covered |

**Blockers**:

- handwriting subcommand of `prepare_multitask_datasets.py` not yet implemented
- Muharaf and PUCIT-OHUL require GCS access or dedicated VM for full harmonization run
- NONE class sampling cap strategy not yet defined

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
| degradation | `quality.degradations` | MEDIUM | ≥ 3 types | unknown | TBD |
| handwriting_style | `handwriting_assessment.content_type` | HIGH | All 7 content types | unknown | TBD |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | unknown | TBD |
| mixed_content | `handwriting_assessment.is_mixed` | HIGH | Both pure and mixed pages | unknown | TBD |
| legibility | `handwriting_assessment.legibility` | MEDIUM | All legibility levels | unknown | TBD |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | unknown | TBD |
| background_complexity | `image_properties.background` | LOW | Plain and complex | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Handwriting mixed with dense printed text | `handwriting_assessment.is_mixed` | ⏳ | analysis required |
| Low-contrast handwriting (faint ink, pencil) | `quality.degradations` | ⏳ | analysis required |
| Camera-captured handwritten notes (glare, perspective) | `capture_method.method` = camera_smartphone | ⏳ | analysis required |
| Historical handwriting (pre-1900 letterforms) | `image_properties.document_age` = historical | ⏳ | analysis required |
| Non-Latin handwriting scripts (Arabic cursive, Devanagari) | `language.script_code` | ⏳ | analysis required |
| Sparse handwriting on complex printed forms | `structure.layout_type` + `handwriting_assessment.presence` | ⏳ | analysis required |
| Handwriting on noisy/degraded paper (bleed-through, stains) | `quality.degradations` | ⏳ | analysis required |
| Handwritten mathematical notation | `handwriting_assessment.content_type` = specialized | ⏳ | absent from training data |
| Illegible handwriting (ILLEGIBLE class) | `handwriting_assessment.legibility` | ⏳ | absent from training; only in OOD |
| Multi-script handwriting on same page | `language.is_mixed_script` | ⏳ | analysis required |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | handwriting_presence=SUBSTANTIAL, script=Arab, text_direction=rtl | SigLIP 2 | Specifically includes ≥ 20 ILLEGIBLE pages (class absent from training). Tests rtl handwriting stress. |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc if access denied) | handwriting_presence=DOMINANT, script=HANS/HANT | SigLIP 2 | 2–4 week access request for CASIA. |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | handwriting_presence=DOMINANT, script=Deva | SigLIP 2 | Non-Latin script handwriting stress. |
| 5d. Specialized content handwriting | 50 | Internal collection / TBD | content_type=specialized (math notation, engineering drawings) | SigLIP 2 | Class absent from training data. |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 5, P0)

### Missing OOD Sub-sources

- KHATT dataset — acquisition path to be confirmed; must verify ILLEGIBLE page count ≥ 20
- CASIA-HWDB access request — 2–4 week lead time; SCUT-HCCDoc identified as fallback
- IIIT-INDIC — acquisition path to be confirmed
- Specialized content (math, engineering) — sourcing strategy TBD

### OOD Leakage Risk

**Level**: MEDIUM

KHATT and CASIA-HWDB are not in the training dataset pool, so leakage risk from dataset overlap is LOW. The ILLEGIBLE class in KHATT (5a) intentionally tests a class absent from training — this is expected behavior, not leakage. Risk is MEDIUM overall because COCO-Text (a training source) and some OOD images may share document origins; SHA256 dedup required.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-2 (legibility_cls) | Shares exact same training dataset | Legibility must be set to N/A for all NONE presence images — label dependency enforced during assembly |
| SIG-G4-3 (content_type_cls) | Shares exact same training dataset | content_type must be set to n/a for all NONE presence images — same dependency |
| SIG-G4-4 (presence_reg) | Shares training dataset; presence_cls is discretized version of presence_reg output | Presence class boundaries must align with presence_score midpoint mapping (NONE: 0–0.01, SPARSE: 0.01–0.10, MODERATE: 0.10–0.30, SUBSTANTIAL: 0.30–0.60, DOMINANT: 0.60–1.00) |
| SIG-G4-5 (legibility_reg) | Shares training dataset | Legibility score must be consistent with legibility class assignments |

### Split Leakage Risk

**Level**: MEDIUM

All five G4 heads share the same training dataset. Global split registry (SHA256-keyed) required to ensure consistent train/val/test splits across all G4 head training manifests. A HierText image in the presence_cls val set must also be in the val set for legibility_cls, content_type_cls, presence_reg, and legibility_reg.

### Label Convention

Presence levels use UPPER_SNAKE_CASE enum values (NONE, SPARSE, MODERATE, SUBSTANTIAL, DOMINANT). The `n/a` convention for absent-handwriting secondary heads uses lowercase with slash. Boundaries are area-ratio based and must be applied consistently across all G4 head labels derived from the same source polygon annotations.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G4P-G01 | — | handwriting subcommand of prepare_multitask_datasets.py not implemented | Phase 3 dataset prep deprioritized | Implement subcommand following script/orientation/shadow pattern | 2 days |
| G4P-G02 | — | Muharaf and PUCIT-OHUL GCS-only locally — full harmonize run blocked | Local dev environment lacks GCS dataset copies | Run harmonize_handwriting_labels.py on GCS VM or download datasets | 1 day |
| G4P-G03 | — | NONE class sampling strategy undefined — naive inclusion creates severe class imbalance | Printed negatives (DocLayNet, TableBank, RVL-CDIP) vastly outnumber positives | Define NONE class cap relative to positive count; implement in subcommand | 0.5 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G4P-G04 | SPARSE class boundary (1–10%) may have low annotation precision from model_derived strategy | Polygon-based area ratio has measurement error near class boundaries | Add VLM validation sampling at Tier 2 for images near SPARSE/MODERATE boundary | 1 day |
| G4P-G05 | No explicit MODERATE class examples in current dry-run count | model_derived strategy may not produce reliable MODERATE labels without HierText polygon quality gate | Audit HierText polygon quality; set minimum polygon area threshold | 0.5 days |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G4P-G06 | Aged / historical handwriting underrepresented (pre-1900 letterforms) | Source historical handwritten documents; add to training pool |
| G4P-G07 | Engineering form handwriting (fill-in forms) not explicitly targeted | Include FUNSD and similar form datasets with handwritten fill-ins |

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
