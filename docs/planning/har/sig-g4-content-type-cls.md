# Head Adequacy Review: content_type_cls (SIG-G4-3)

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
| Head ID | SIG-G4-3 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | content_type_cls (also written as handwriting_content_type_cls) |
| Task Type | Classification — 7 classes (n/a / digits / alphanumeric / prose / cursive / mixed / specialized) |
| Output Format | Softmax over 7 content types |
| Priority | P1 |
| Performance Target | Accuracy ≥ 85% |
| Primary L2 Field | `handwriting_assessment.content_type` (7-class enum) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5) — all trained on the same dataset |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.content_type` _(7-class enum: n/a / digits / alphanumeric / prose / cursive / mixed / specialized)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact or tier_1_annotation preferred; most datasets require class inference from corpus metadata

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for relevant datasets)_

### Class Definitions

| Class | Description |
| --- | --- |
| n/a | No handwriting present (NONE presence level) — content type not applicable |
| digits | Handwritten numerals only (e.g., form fields, tabular data) |
| alphanumeric | Handwritten mix of letters and digits without connected prose flow |
| prose | Handwritten connected text forming sentences or paragraphs (print style) |
| cursive | Handwritten connected text in cursive / joined letterform style |
| mixed | Combination of two or more content types on the same page |
| specialized | Specialized notation: mathematical symbols, musical notation, engineering drawings, chemical formulae |

### Critical Gap: `specialized` Class

**`specialized` is absent from all training datasets.** This class is sourced exclusively from OOD-Handwriting sub-source 5d (50 images of math notation and engineering drawings). The model will not have training signal for this class — it is an open-set test class for this head.

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| HierText | 8,281 | _(analysis required — corpus-level prose/mixed inference)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| COCO-Text | 63,686 | _(analysis required — corpus-level inference)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| IAM | _(analysis required)_ | _(all prose by design)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Muharaf | _(analysis required — GCS-only locally)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| PUCIT-OHUL | _(analysis required — GCS-only locally)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| Nepali Handwritten | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| NIST SD-19 | _(analysis required)_ | _(digits + alphanumeric by design)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |
| FUNSD | _(analysis required)_ | _(alphanumeric + mixed form fill-ins)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ | _(analysis required)_ |

### Usable Pool Summary

- **Total usable before enrichment**: _(analysis required)_
- **Training target**: 102,000+ images (shared with all G4 heads)
- **Gap**: `specialized` class entirely absent; `cursive` vs `prose` distinction requires per-image annotation; `digits` and `alphanumeric` well-covered by NIST SD-19 and FUNSD

### VLM Validation Sampling Tier

_(analysis required — cursive/prose boundary is subjective and likely requires Tier 2 or 3 VLM validation; specialized class Tier 3)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-03-A | `specialized` class absent from all training datasets — only covered in OOD | HIGH — open-set behavior only; 50 OOD examples may be insufficient for reliable evaluation |
| KI-G4-03-B | `cursive` vs `prose` distinction is style-based and highly subjective — low inter-annotator agreement expected | HIGH — may require collapsing to a single `prose_cursive` class or strict IAA threshold |
| KI-G4-03-C | Most datasets do not carry explicit content_type annotations — requires corpus-level assignment or VLM per-image labeling | HIGH — significant annotation effort |
| KI-G4-03-D | `mixed` class definition is broad — any two content types co-occurring qualifies; high risk of over-labeling as mixed | MEDIUM — needs clear boundary rules |

### Remediation Path

_(analysis required — initial steps: 1) define content_type inference rules per dataset, 2) decide cursive/prose merge question with model consensus, 3) run VLM for ambiguous cases)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 102,000+ images (shared with all G4 heads) |
| Assembly Status | ⏳ Not started |
| Current Count | _(analysis required)_ |
| `specialized` Class | OOD-only — intentionally absent from training; open-set behavior expected |
| n/a Class | All NONE-presence images receive n/a — label dependency on SIG-G4-1 |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Class Distribution Requirements

| Class | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- |
| n/a | Set by NONE-presence count | Printed negatives | LOW |
| digits | ≥ 5% of handwriting images | NIST SD-19 | LOW — well-covered |
| alphanumeric | ≥ 10% of handwriting images | FUNSD, NIST SD-19 | LOW |
| prose | ≥ 30% of handwriting images | IAM, HierText | MEDIUM — print style vs cursive disambiguation |
| cursive | ≥ 25% of handwriting images | Muharaf, PUCIT-OHUL | HIGH — requires VLM labeling; GCS-only locally |
| mixed | ≥ 20% of handwriting images | FUNSD, COCO-Text | MEDIUM — over-labeling risk |
| specialized | 0 (OOD only) | OOD sub-source 5d only | CRITICAL — open-set gap |

**Blockers**:

- handwriting subcommand of `prepare_multitask_datasets.py` not yet implemented
- Content type annotation strategy not defined for most datasets (no existing L2 field)
- `cursive` vs `prose` decision requires explicit model-level consensus
- `specialized` class training strategy requires explicit decision (accept as open-set vs. source examples)

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
| content_style | `handwriting_assessment.content_type` | CRITICAL | All 6 non-n/a classes in training | unknown | TBD |
| writing_instrument | _(no dedicated L2 field)_ | MEDIUM | Pen, pencil, marker represented | unknown | TBD |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | unknown | TBD |
| document_type | `domain.document_type` | HIGH | ≥ 4 types (letter, form, note, notebook) | unknown | TBD |
| mixed_content | `handwriting_assessment.is_mixed` | HIGH | Both pure and mixed pages | unknown | TBD |
| background_complexity | `image_properties.background` | MEDIUM | Plain and complex (forms vs free pages) | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Specialized notation (math, music, engineering) | `handwriting_assessment.content_type` = specialized | ⏳ | entirely absent from training; OOD-only |
| Cursive script in non-Latin alphabets (Arabic, Devanagari) | `language.script_code` + `handwriting_assessment.content_type` | ⏳ | analysis required |
| Mixed handwriting and printed text on forms | `structure.layout_type` + `handwriting_assessment.is_mixed` | ⏳ | analysis required |
| Digit-only handwriting in table/form cells | `handwriting_assessment.content_type` = digits | ⏳ | analysis required |
| Historical cursive letterforms (pre-1900) | `image_properties.document_age` = historical | ⏳ | analysis required |
| Mixed-script handwriting (e.g., Latin + Arabic on same page) | `language.is_mixed_script` | ⏳ | analysis required |
| Low-density handwriting (single line on otherwise blank page) | `structure.text_density` | ⏳ | analysis required |
| Camera-captured handwritten notes (perspective, glare) | `capture_method.method` = camera_smartphone | ⏳ | analysis required |
| Shorthand notation (Gregg, Pitman) | _(no L2 field)_ | ⏳ | absent from all training; not currently planned |
| Signature-only pages | `handwriting_assessment.content_type` (boundary case: alphanumeric or cursive?) | ⏳ | definition ambiguity |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | content_type=cursive, script=Arab, text_direction=rtl | SigLIP 2 | Primary cursive OOD stress; non-Latin cursive absent from most training sources |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc if access denied) | content_type=prose or mixed, script=HANS/HANT | SigLIP 2 | CJK handwriting — stroke-based rather than alphabetic; tests content_type generalization to non-alphabetic scripts |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | content_type=prose or alphanumeric, script=Deva | SigLIP 2 | Devanagari handwriting content type stress |
| 5d. Specialized content handwriting | 50 | Internal collection / TBD | content_type=specialized (math notation, engineering drawings) | SigLIP 2 | THE only source of `specialized` class evaluation data — critical for this head |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 5, P0)

### Missing OOD Sub-sources

- Specialized content sourcing strategy not defined (math notebooks, engineering schematics, musical scores)
- 50 images for `specialized` class may be insufficient for statistical evaluation — consider increasing to 100–150
- Shorthand notation not currently covered in OOD design

### OOD Leakage Risk

**Level**: MEDIUM

`specialized` class in OOD intentionally tests open-set behavior. Primary risk is that `mixed` training examples could partially overlap with OOD images if sourcing is not carefully controlled. SHA256 dedup required against all training sources.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-1 (presence_cls) | Shares training dataset; n/a content_type applies to NONE presence | All images with presence=NONE must have content_type=n/a; enforced during assembly |
| SIG-G4-2 (legibility_cls) | Shares training dataset | content_type and legibility must be jointly consistent on same images (e.g., digits content_type should rarely have POOR legibility in clean datasets like NIST SD-19) |
| SIG-G4-4 (presence_reg) | Shares training dataset | Presence score consistency — content_type informs expected presence range validation |

### Split Leakage Risk

**Level**: MEDIUM

Same as all G4 heads — global split registry required. Additional risk specific to this head: if content_type labels are inferred at corpus level (all IAM = prose, all NIST = digits) rather than per-image, split stratification cannot use label values meaningfully. Must stratify by dataset source + SHA256.

### Label Convention

7-class enum with lowercase values (n/a, digits, alphanumeric, prose, cursive, mixed, specialized). The n/a value uses lowercase to match the convention for absent-context labels in the handwriting assessment group. The `specialized` class explicitly excludes standard annotated cursive/prose — it must require expert-level notation that a general reader cannot parse without domain knowledge.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G4C-G01 | — | handwriting subcommand of prepare_multitask_datasets.py not implemented | Phase 3 dataset prep deprioritized | Implement subcommand (shared blocker with all G4 heads) | 2 days (shared) |
| G4C-G02 | — | `specialized` class absent from all training data — explicit decision required | No training corpus contains specialized notation pages | Decide: accept as open-set (recommended) OR source ~200 specialized notation examples; document decision | 0.5 days decision |
| G4C-G03 | — | Content type annotation strategy undefined for most datasets (no existing L2 field) | Labels not collected during dataset assembly | Define per-dataset inference rules (corpus-level or VLM per-image); implement in harmonize script | 1 day |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G4C-G04 | `cursive` vs `prose` boundary is subjective — potential for low inter-annotator agreement | Style-based distinction with no pixel-level ground truth | Run IAA measurement on 100 images; if IAA < 0.7, collapse into single `prose_cursive` class | 1 day |
| G4C-G05 | `mixed` class over-labeling risk — any co-occurrence qualifies; may dominate training | Broad class definition | Set minimum area threshold for each component before qualifying as mixed (e.g., each component ≥ 10% of page) | 0.5 days |
| G4C-G06 | OOD specialized class sample count (50) may be too small for reliable evaluation statistics | Budget constraint on OOD acquisition | Increase to 100–150 specialized examples if sourcing allows | 1 day |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G4C-G07 | Shorthand notation (Gregg, Pitman) not covered in training or OOD | Source historical shorthand documents; add to specialized subclass |
| G4C-G08 | Signature-only pages have ambiguous content_type (alphanumeric or cursive?) | Define explicit labeling rule for signatures; add to harmonize script documentation |
| G4C-G09 | Musical notation handwriting entirely absent | Source music manuscript images; add to specialized OOD pool |

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
