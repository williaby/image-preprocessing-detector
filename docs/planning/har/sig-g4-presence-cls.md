# Head Adequacy Review: presence_cls (SIG-G4-1)

> **Status**: Needs Work — Analysis Complete
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
| Head ID | SIG-G4-1 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | presence_cls (also written as handwriting_presence_cls) |
| Task Type | Classification — 5 classes (NONE / MARGINAL / PARTIAL / SUBSTANTIAL / DOMINANT) |
| Output Format | Softmax over 5 presence levels |
| Priority | P1 |
| Performance Target | Macro F1 ≥ 0.78 |
| Primary L2 Field | `handwriting_assessment.presence` (5-class enum) |
| Supporting L2 Field | `handwriting_assessment.presence_score` (0-1 continuous; also used by SIG-G4-4) |
| Shared-Data Heads | All G4 heads (SIG-G4-2 through SIG-G4-5) — all trained on the same 60K dataset |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.presence` (5-class enum: NONE / MARGINAL / PARTIAL / SUBSTANTIAL / DOMINANT)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact preferred for DOMINANT (pure handwriting) and NONE (pure printed); tier_1_annotation via polygon pixel-ratio for intermediate classes.

### Class Definitions

The scaffolded file used NONE/SPARSE/MODERATE/SUBSTANTIAL/DOMINANT. The task prompt specifies NONE/MARGINAL/PARTIAL/SUBSTANTIAL/DOMINANT with different area thresholds. This review uses the task prompt definitions:

| Class | Area Threshold | Description |
| --- | --- | --- |
| NONE | 0% | No handwriting present; born-digital or purely printed content |
| MARGINAL | < 10% | Incidental handwriting; typed form with a signature, a single annotation |
| PARTIAL | 10–50% | Mixed document; printed instructions with handwritten answers |
| SUBSTANTIAL | 50–90% | Predominantly handwritten with some printed elements |
| DOMINANT | > 90% | Essentially all handwriting; pure cursive/print manuscript pages |

### Label Harmonization Strategy

Labels are derived via three strategies applied per dataset:

- **all_handwritten**: IAM, NIST-SD2, Muharaf, PUCIT-OHUL — all pages assigned DOMINANT by design (pure handwriting corpora)
- **model_derived**: HierText, COCO-Text — presence class computed from ratio of handwriting polygon area to total page area using native polygon annotations
- **all_printed**: DocLayNet, TableBank, RVL-CDIP — all pages assigned NONE (born-digital or typed negatives)

`scripts/harmonize_handwriting_labels.py` produces a BINARY presence flag only. The 5-class label conversion is **not yet implemented**.

### Candidate Source Datasets

| Dataset | Total Images | Presence Classes Covered | L2 Field Populated | Conf ≥ 0.7 | Strategy | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| IAM | ~13,000 pages | DOMINANT only | No | Yes (by design) | all_handwritten | Yes — DOMINANT |
| NIST-SD2 | ~10,000 pages | DOMINANT / SUBSTANTIAL | No | Yes (by design) | all_handwritten | Yes — DOMINANT |
| Muharaf | ~20,000 pages | DOMINANT only | No (GCS-only locally) | Yes (by design) | all_handwritten | Yes — DOMINANT (after GCS run) |
| PUCIT-OHUL | ~7,000 pages | DOMINANT only | No (GCS-only locally) | Yes (by design) | all_handwritten | Yes — DOMINANT (after GCS run) |
| HierText | 8,281 pages | MARGINAL / PARTIAL (natural scene mix) | No | Conditional on polygon quality | model_derived | Yes — intermediate classes ONLY |
| COCO-Text | 63,686 images | NONE / MARGINAL (mostly scene text, minimal HW) | No | Conditional on polygon quality | model_derived | Partial — mostly NONE/MARGINAL |
| DocLayNet | 81,000 pages | NONE only | Yes (all_printed) | Yes | all_printed | Yes — NONE |
| TableBank | 278,000 pages | NONE only | No | Yes | all_printed | Yes — NONE (capped) |
| RVL-CDIP | ~400,000 pages | NONE / MARGINAL (some handwritten annotations) | No | Partial | all_printed | Yes — NONE (capped) |
| FUNSD | ~200 forms | MARGINAL / PARTIAL (forms with fill-ins) | No | Conditional | model_derived | Potential — intermediate classes |

### Critical Gap: Intermediate Classes

- **MARGINAL / PARTIAL / SUBSTANTIAL** classes have **zero labeled training examples** in the current plan.
- HierText polygon annotations can yield MARGINAL and PARTIAL labels via pixel-ratio computation, but the implementation does not exist.
- SUBSTANTIAL class (50–90% handwriting) requires documents with mixed printed structure and dense handwritten content — no current source provides this naturally at scale.
- Synthetic composition (programmatically overlaying handwriting onto printed document backgrounds) is a viable secondary path for MARGINAL and PARTIAL classes.

### Usable Pool Summary

- **DOMINANT class**: ~50,000 images (IAM ~13K + NIST-SD2 ~10K + Muharaf ~20K + PUCIT-OHUL ~7K) — adequate after GCS access
- **NONE class**: >350,000 images — vastly over-represented; requires aggressive sampling cap (target ≤ 12,000 after cap)
- **MARGINAL class**: ~0 labeled examples — requires model_derived labeling on HierText/COCO-Text; target 12,000
- **PARTIAL class**: ~0 labeled examples — requires model_derived labeling on HierText or synthetic composition; target 12,000
- **SUBSTANTIAL class**: ~0 labeled examples — no natural source; requires synthetic composition; target 12,000
- **Total gap**: 3 of 5 classes have zero labeled examples; assembly is blocked

### VLM Validation Sampling Tier

- DOMINANT and NONE classes: Tier 1 (automated assignment, spot-check 2%)
- MARGINAL and PARTIAL classes: Tier 2 (VLM validation on 20% of pixel-ratio assigned images — boundary precision is critical near the 10% and 50% thresholds)
- SUBSTANTIAL class: Tier 2 or Tier 3 (synthetic composition requires VLM quality gate before use)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| HW-PRES-D01 | harmonize_handwriting_labels.py | handwriting_assessment.presence | Script outputs binary flag; 5-class enum not implemented | Open — blocks all assembly |
| HW-PRES-D02 | HierText | handwriting_assessment.presence | Polygon area ratio to presence class mapping not implemented | Open |
| HW-PRES-D03 | COCO-Text | handwriting_assessment.presence | COCO-Text is predominantly scene text; handwriting polygon coverage is sparse — exact count unknown | Open — requires audit |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-01 | Muharaf and PUCIT-OHUL are GCS-only locally — full harmonize run requires GCS access or VM | HIGH — ~27K DOMINANT images unavailable for dry-run |
| KI-G4-02 | NONE class is trivially abundant; naive inclusion creates severe class imbalance (>10:1 ratio) | HIGH — sampling cap and class weights required |
| KI-G4-03 | 5-class label conversion not implemented in harmonize_handwriting_labels.py | P0 BLOCKER — head cannot train without 5-class labels |
| KI-G4-04 | MARGINAL/PARTIAL/SUBSTANTIAL classes have zero labeled examples from any source | P0 BLOCKER — 3 of 5 classes missing entirely |
| KI-G4-05 | handwriting subcommand of prepare_multitask_datasets.py not yet implemented | P0 BLOCKER — assembly pipeline incomplete |
| KI-G4-06 | CJK, Devanagari, and Cyrillic handwriting absent from all training sources | HIGH — script diversity severely limited to Latin/Arabic/Urdu only |

### Remediation Path

1. Implement 5-class label conversion in `scripts/harmonize_handwriting_labels.py`
2. Implement pixel-ratio area computation for HierText and COCO-Text polygon annotations
3. Implement SUBSTANTIAL class via synthetic composition script (overlay handwriting on printed pages)
4. Run full harmonize on GCS VM to include Muharaf and PUCIT-OHUL
5. Define and enforce NONE class sampling cap (12,000 images max)
6. Implement handwriting subcommand in `prepare_multitask_datasets.py`
7. Audit class balance and apply sampling weights before assembly

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 60,000 images |
| Assembly Status | Blocked — label conversion and assembly pipeline not implemented |
| Current Count | 38,967 records (dry-run estimate, binary labels only); 0 images with valid 5-class labels |
| Label Strategy | all_handwritten (IAM/NIST-SD2/Muharaf/PUCIT-OHUL) + model_derived (HierText/COCO-Text pixel-ratio) + synthetic composition (SUBSTANTIAL class) + all_printed (negatives, capped) |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Class Distribution Requirements

| Class | Target Count | Target % | Derivation Method | Risk |
| --- | --- | --- | --- | --- |
| NONE | 12,000 | 20% | all_printed (capped from >350K available) | LOW — over-representation risk; cap required |
| MARGINAL | 12,000 | 20% | model_derived (HierText/COCO-Text polygon pixel-ratio) | HIGH — implementation missing; boundary precision near 10% threshold |
| PARTIAL | 12,000 | 20% | model_derived (HierText) + synthetic composition fallback | HIGH — sparse natural examples; synthetic composition may be required |
| SUBSTANTIAL | 12,000 | 20% | synthetic composition (overlay handwriting on printed backgrounds) | HIGH — no natural source; requires new generation script |
| DOMINANT | 12,000 | 20% | all_handwritten (IAM + NIST-SD2 + Muharaf + PUCIT-OHUL, capped) | LOW — ~50K available once GCS access obtained |

**Blockers**:

- 5-class label conversion not implemented (P0)
- MARGINAL/PARTIAL/SUBSTANTIAL classes have zero labeled examples (P0)
- handwriting subcommand of `prepare_multitask_datasets.py` not implemented (P0)
- Muharaf and PUCIT-OHUL require GCS VM access for full harmonization run

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: Estimated 22/100 (pre-assembly projection; full scoring blocked until assembly completes)

The primary diversity failure is class balance: 3 of 5 classes have zero examples. Secondary failures are script diversity (only Latin/Arabic/Urdu) and capture method diversity (mixed content pages skew toward camera capture which is poorly represented).

| Dimension | L2 Field | Relevance | Target | Current Estimate | Score |
| --- | --- | --- | --- | --- | --- |
| class_balance | `handwriting_assessment.presence` | CRITICAL | ~12,000 per class | NONE: >350K available; DOMINANT: ~50K; MARGINAL/PARTIAL/SUBSTANTIAL: 0 | 10/100 |
| script_diversity | `language.script_code` | HIGH | ≥ 5 scripts (LATN, ARAB, URDU, HANS, DEVA) | LATN (IAM), ARAB (Muharaf), URDU (PUCIT-OHUL) — CJK/Deva/Cyrillic absent | 25/100 |
| mixed_content | `handwriting_assessment.is_mixed` | HIGH | ≥ 30% mixed (printed + handwritten) pages | Near zero — mixed pages require intermediate class examples which don't exist | 5/100 |
| capture_method | `capture_method.method` | HIGH | ≥ 3 methods (born_digital, scanner, camera) | born_digital (DocLayNet NONE), scanner (IAM/NIST-SD2 DOMINANT); camera: minimal | 30/100 |
| handwriting_style | `handwriting_assessment.content_type` | HIGH | All 7 content types (cursive, print, shorthand, etc.) | Cursive/print from IAM; limited variation elsewhere | 35/100 |
| document_age | `image_properties.document_age` | MEDIUM | All 3 ages (modern, aged, historical) | Mostly modern; aged/historical virtually absent | 15/100 |
| color_mode | `image_properties.color_mode` | MEDIUM | ≥ 2 modes (color, grayscale) | Grayscale dominant (IAM, NIST-SD2); some color in scene text datasets | 40/100 |
| degradation | `quality.degradations` | MEDIUM | ≥ 3 types | IAM/NIST-SD2 are clean scans; degraded HW examples scarce | 20/100 |
| domain | `domain.level1` | MEDIUM | ≥ 5 domains | Academic (IAM), financial forms (NIST-SD2), natural scene (HierText); limited domain spread | 35/100 |
| resolution | `resolution.category` | MEDIUM | ≥ 3 tiers | Scanner-sourced datasets are generally 300 DPI; limited variation | 40/100 |
| layout_type | `structure.layout_type` | LOW | ≥ 3 types | Pure manuscript (DOMINANT); born-digital structured (NONE); mixed layouts absent | 20/100 |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | Limited variation across sources | 35/100 |
| document_type | `domain.document_type` | MEDIUM | ≥ 4 types | Letters/notes (IAM), forms (NIST-SD2), scene images (HierText); limited variety | 30/100 |
| background_complexity | `image_properties.background` | LOW | Plain and complex | Plain background dominant; complex backgrounds only in scene text datasets | 35/100 |

**Key Dimension Findings**:

- **Class balance is the dominant failure** — three classes have zero examples, which will guarantee near-zero F1 on those classes regardless of all other diversity properties.
- **Script diversity is critically limited** — SigLIP 2's visual features will be heavily biased toward Latin-family handwriting. The model will encounter CJK, Devanagari, and Cyrillic handwriting in production (these appear in the OOD set) with no training signal.
- **Mixed content** is the defining characteristic of MARGINAL/PARTIAL/SUBSTANTIAL — without these class examples, the model cannot learn to distinguish a form with a signature (MARGINAL) from a notebook with dense handwritten notes (SUBSTANTIAL).

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 18/100 (pre-assembly projection)

| Wild Condition | L2 Field Evidence | Dataset Coverage | Status | Severity |
| --- | --- | --- | --- | --- |
| Typed form with single handwritten signature (MARGINAL archetype) | `handwriting_assessment.is_mixed`, `presence` = MARGINAL | No dataset currently provides this; FUNSD has form fill-ins but coverage is tiny (~200 images) | Absent | CRITICAL — defines the MARGINAL class |
| School exercise: printed instructions + handwritten answers (PARTIAL archetype) | `handwriting_assessment.is_mixed`, `presence` = PARTIAL | HierText may contain some examples via polygon ratio; coverage unquantified | Partial at best | CRITICAL — defines the PARTIAL class |
| Research notebook: printed headings + extensive handwritten notes (SUBSTANTIAL archetype) | `handwriting_assessment.is_mixed`, `presence` = SUBSTANTIAL | No natural source identified; requires synthetic composition | Absent | CRITICAL — defines the SUBSTANTIAL class |
| Faded or aged handwriting approaching illegibility | `quality.degradations`, `image_properties.document_age` | Clean scanner captures dominate DOMINANT class; degraded HW absent | Absent | HIGH — faded ink could cause misclassification to MARGINAL or NONE |
| Camera-captured handwritten notes with glare and perspective distortion | `capture_method.method` = camera_smartphone | HierText has some camera-captured scene text; IAM is flatbed-scanned only | Partial (scene text only) | HIGH — real-world notebook photography |
| Stamps and rubber impressions (false positive risk — visually similar to handwriting) | `handwriting_assessment.presence` | No dataset explicitly covers stamps as a confounding class | Absent | MEDIUM — rubber stamps may activate handwriting features |
| Colored or highlighted text mimicking handwriting style | `image_properties.color_mode` | Minimal; born-digital NONE sources do include colored text but not as a confounding presence example | Absent | MEDIUM |
| Non-Latin handwriting: Arabic cursive (Muharaf covers training; wild condition is mixed Arabic HW + printed) | `language.script_code` = Arab | Muharaf is pure Arabic HW (DOMINANT only); mixed Arabic HW + printed text absent | Partial (DOMINANT only) | HIGH |
| Non-Latin handwriting: CJK (CASIA-HWDB style) | `language.script_code` = Hans/Hant | Absent from all training sources | Absent | HIGH |
| Non-Latin handwriting: Devanagari | `language.script_code` = Deva | Absent from all training sources | Absent | HIGH |
| Handwritten mathematical notation | `handwriting_assessment.content_type` = specialized | Absent from training; only in OOD-Handwriting 5d (50 images) | OOD only | MEDIUM |
| Multi-script page: printed English + handwritten Arabic annotations | `language.is_mixed_script` | No training source provides this; very common in real bilingual documents | Absent | MEDIUM |
| Degraded form: bleed-through obscuring handwriting | `quality.degradations` = bleed_through | NIST-SD2 has some form degradation; systematic coverage absent | Sparse | MEDIUM |

**Key Finding**: The three archetype wild conditions (MARGINAL / PARTIAL / SUBSTANTIAL class representatives) are all absent from training data. These conditions ARE the classes the head must learn — their absence is not a diversity gap in the traditional sense, it is a direct statement of the class coverage failure identified in Section 2.

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | handwriting_presence=SUBSTANTIAL, script=Arab, text_direction=rtl | SigLIP 2 | Specifically includes ≥ 20 ILLEGIBLE pages (legibility class absent from training). Tests RTL handwriting stress. |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc if access denied) | handwriting_presence=DOMINANT, script=HANS/HANT | SigLIP 2 | 2–4 week access request for CASIA. Tests CJK handwriting not in training. |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | handwriting_presence=DOMINANT, script=Deva | SigLIP 2 | Non-Latin script handwriting stress. Tests Devanagari not in training. |
| 5d. Specialized content handwriting | 50 | Internal collection / TBD | content_type=specialized (math notation, engineering drawings) | SigLIP 2 | Class absent from training data. |

### OOD Acquisition Status

**Status**: Not started (Phase 5, P0)

### OOD Design Assessment

The OOD design is structurally sound for its stated purpose of evaluating robustness on conditions absent from training. The 4 sub-sources cover the three key absent scripts (Arabic RTL, CJK, Devanagari) and a specialized content class. However:

- The OOD set covers only DOMINANT (sub-sources 5b, 5c) and SUBSTANTIAL (5a) classes. MARGINAL/PARTIAL classes are not represented in OOD evaluation.
- With only 500 images and ~4 scripts, the OOD set cannot serve as a proxy for the broader script coverage gap in training. It is adequate for post-training robustness auditing but does not substitute for training data.
- The CASIA-HWDB 2–4 week access lead time is a scheduling risk.

### OOD Leakage Risk

**Level**: MEDIUM

KHATT and CASIA-HWDB are not in the training dataset pool, so direct overlap risk is LOW. COCO-Text (a training source) and some HierText images may share document origins with OOD scene text images; SHA256 + pHash dedup (Hamming ≤ 5) is required. The ILLEGIBLE class in KHATT (5a) intentionally tests a class absent from training — this is expected evaluation behavior.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-2 (legibility_cls) | Shares exact same training dataset | `legibility` must be set to `NOT_APPLICABLE` for all NONE presence images — label dependency enforced during assembly |
| SIG-G4-3 (content_type_cls) | Shares exact same training dataset | `content_type` must be set to `not_applicable` for all NONE presence images — same dependency |
| SIG-G4-4 (presence_reg) | Shares training dataset; presence_cls is discretized version of presence_reg output | Presence class boundaries must align with presence_score midpoint mapping: NONE: 0–0.05, MARGINAL: 0.05–0.10, PARTIAL: 0.10–0.50, SUBSTANTIAL: 0.50–0.90, DOMINANT: 0.90–1.00 |
| SIG-G4-5 (legibility_reg) | Shares training dataset | Legibility score must be consistent with legibility class assignments across all G4 heads |

### Split Leakage Risk

**Level**: MEDIUM

All five G4 heads share the same training dataset. Global split registry (SHA256-keyed) required to ensure consistent train/val/test splits across all G4 head training manifests. A HierText image assigned to the presence_cls val set must also appear in the val set for legibility_cls, content_type_cls, presence_reg, and legibility_reg.

### Label Convention

Presence levels use UPPER_SNAKE_CASE enum values (NONE, MARGINAL, PARTIAL, SUBSTANTIAL, DOMINANT). The `not_applicable` convention for absent-handwriting secondary heads uses lowercase with underscore. Area-ratio boundaries must be applied consistently across all G4 head labels derived from the same polygon annotations. The boundary between MARGINAL and PARTIAL (10%) and between PARTIAL and SUBSTANTIAL (50%) are the highest-risk class confusion points and require VLM validation sampling (Tier 2).

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before any assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-PRES-G01 | 5-class label conversion not implemented — `harmonize_handwriting_labels.py` produces binary flag only | Phase 3 dataset prep was scoped to binary detection; 5-class schema designed later | Extend harmonize script: add `all_handwritten` → DOMINANT mapping, `all_printed` → NONE mapping, and pixel-ratio logic for `model_derived` sources | 2 days |
| HW-PRES-G02 | MARGINAL class has zero labeled examples — pixel-ratio computation on HierText/COCO-Text not implemented | No implementation exists to measure handwriting polygon area as fraction of page area | Implement pixel-ratio labeling using HierText polygon annotations; filter to pages where 1–10% of area is handwritten | 2 days |
| HW-PRES-G03 | PARTIAL class has zero labeled examples — HierText may yield some but coverage is uncertain | Same as HW-PRES-G02; requires implementation and count audit | Implement pixel-ratio, then audit HierText PARTIAL yield; if insufficient, implement synthetic composition overlay script | 2–4 days |
| HW-PRES-G04 | SUBSTANTIAL class has zero labeled examples — no natural dataset provides 50–90% handwriting coverage at scale | Pure handwriting datasets are DOMINANT; mixed document datasets have little to no handwriting in that range | Implement synthetic composition: programmatically overlay handwriting page crops onto printed document backgrounds at 50–90% area coverage | 3 days |
| HW-PRES-G05 | handwriting subcommand of `prepare_multitask_datasets.py` not implemented | Deprioritized during Stream 4C; other subcommands (script, orientation, shadow, warping) implemented first | Implement following the established subcommand pattern; include NONE class sampling cap enforcement | 2 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-PRES-G06 | CJK handwriting (HANS/HANT) absent from all training sources — SigLIP visual features will be biased toward Latin-family handwriting | No CJK handwriting dataset available locally or on GCS | Source CASIA-HWDB or SCUT-HCCDoc; generate 5,000–10,000 CJK DOMINANT examples to supplement training | 3–5 days (incl. access request) |
| HW-PRES-G07 | Devanagari handwriting absent from all training sources | No Devanagari handwriting dataset in current inventory | Source IIIT-HW or similar Devanagari handwriting dataset (1,000–3,000 images minimum) | 2–3 days |
| HW-PRES-G08 | Cyrillic handwriting absent from all training sources | No Cyrillic handwriting dataset in current inventory | Source HKR dataset (Russian cursive handwriting, ~95K lines) or equivalent; sample ~2,000 page-level images | 2 days |
| HW-PRES-G09 | MARGINAL/PARTIAL class boundary precision low near 10% threshold — pixel-ratio measurement has ±3–5% uncertainty | Polygon annotations in HierText are word-level, not character-level; small handwriting areas may be systematically over- or under-estimated | Apply VLM validation sampling (Tier 2, 20% of boundary-zone images); add ±2% dead-zone around 10% and 50% thresholds to reduce label noise | 1 day |
| HW-PRES-G10 | Degraded handwriting (faded ink, aged paper) absent from DOMINANT/SUBSTANTIAL training examples | IAM and NIST-SD2 are clean flatbed scans; no aged handwriting examples sourced | Apply Augraphy degradation augmentations (ink fade, yellowing, foxing) to existing DOMINANT examples; target 10% of DOMINANT class | 1 day |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| HW-PRES-G11 | Historical handwriting (pre-1900 letterforms) absent from all classes | Source historical manuscript scans (e.g., Bentham Papers, IAM-HistDB) |
| HW-PRES-G12 | Engineering form fill-ins (FUNSD-style) underrepresented in MARGINAL/PARTIAL | Expand FUNSD usage; source additional form fill-in datasets |
| HW-PRES-G13 | Stamps and rubber impressions not explicitly represented as NONE confounders | Add stamp-only page samples to NONE class to train model to reject stamp false positives |

### Total Remediation Estimate

- **P0 Blockers**: ~11–13 days engineering effort to unblock assembly
- **P1 Improvements**: ~9–12 days additional effort before evaluation
- **Total to Evaluation-Ready**: approximately 20–25 engineering days

---

## Section 9 — Multi-Model Consensus

**Consensus Run Date**: 2026-02-23

**Models Consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

**Consensus Confidence**: High (both models rated 9–10/10)

### Analyst Summary

The presence_cls head (SIG-G4-1) is architecturally well-conceived — the 5-class presence schema is meaningful, the training data sources are correctly identified, and the pixel-ratio approach for intermediate class labeling is technically sound. However, the implementation is critically incomplete. Three of five classes have zero labeled examples. The label conversion infrastructure does not exist. The assembly pipeline subcommand is not implemented. Without these, no meaningful training can begin.

The Macro F1 ≥ 0.78 target, while plausible for a well-assembled dataset, is unachievable with the current data plan. The absence of CJK/Devanagari/Cyrillic handwriting creates a systematic bias toward Latin-family scripts that will depress performance on those scripts in production.

### Consensus Questions and Findings

**Q1: Is pixel-ratio measurement from polygon annotations sufficient for intermediate class labels?**

Both models agreed: yes, pixel-ratio from HierText/COCO-Text polygon annotations is the correct and most feasible approach. It provides tier_1_annotation quality for MARGINAL and PARTIAL classes. Implementation priority is P0. The ±3–5% measurement uncertainty near class boundaries requires a VLM validation gate (Tier 2, 20% sample of boundary-zone images) and a dead-zone buffer of ±2% around the 10% and 50% thresholds.

**Q2: Is absence of CJK/Devanagari/Cyrillic handwriting a P0 blocker?**

Gemini 2.5 Pro rated this P0 (unachievable F1 without these scripts). Gemini 3 Pro treated it as secondary to the label conversion gap, implicitly P1. Synthesis: the absence is a **P1 blocker** rather than P0. The head can reach a partial F1 score on Latin/Arabic/Urdu data, but the Macro F1 ≥ 0.78 target will not be achievable in production across all scripts. The five label conversion / class coverage gaps (HW-PRES-G01 through G05) are the true P0 blockers that prevent training from starting at all.

**Q3: Does binary-only label implementation constitute a P0 blocker?**

Both models: unanimous YES. A 5-class classifier trained on binary labels (positive/negative) would produce a 2-class model, not a 5-class model. The 5-class label conversion is a prerequisite for any training run on this head. HW-PRES-G01 is a hard P0 blocker.

**Q4: Is the OOD-Handwriting design adequate?**

Both models found the OOD design structurally adequate for its stated purpose (post-training robustness auditing on absent scripts and content types). The 500-image / 4-sub-source design covers the three most important absent scripts (Arabic RTL, CJK, Devanagari) and a specialized content type. However, the OOD set does not address the MARGINAL/PARTIAL/SUBSTANTIAL class gap in training; it evaluates only DOMINANT and SUBSTANTIAL presences on held-out scripts. The 500-image size is adequate for robustness auditing but insufficient to drive script coverage improvements — that requires training data, not OOD data.

**Q5: Overall adequacy rating**

Both models: **Blocked**. Training cannot meaningfully begin until the five P0 gaps are resolved. The dataset design identifies the right sources and the right approach, but the implementation is at 0% for the critical intermediate classes.

### Scoring Summary

| Component | Weight | Score | Weighted Score | Rationale |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 30/100 | 10.5 | DOMINANT and NONE pools are adequate; MARGINAL/PARTIAL/SUBSTANTIAL have zero examples; pixel-ratio approach identified but not implemented |
| 14-Dimension Coverage | 25% | 22/100 | 5.5 | Class balance is the dominant failure (3 of 5 classes absent); script diversity critically limited; mixed content absent |
| Wild Condition Coverage | 20% | 18/100 | 3.6 | All three archetype wild conditions (MARGINAL / PARTIAL / SUBSTANTIAL archetypes) are absent; non-Latin handwriting absent |
| OOD Design Quality | 20% | 62/100 | 12.4 | Structurally sound design; correct sub-sources; 4 key gaps covered; adequate size for robustness auditing; scheduling risk from CASIA-HWDB access time |
| **Overall** | 100% | — | **32.0** | — |

**Overall Score**: 32/100

**Grade**: F — Blocked

**Final Rating**: Blocked

### Top Recommendations

1. **Immediate P0**: Implement 5-class label conversion in `harmonize_handwriting_labels.py` — map `all_handwritten` sources to DOMINANT, `all_printed` sources to NONE, and implement pixel-ratio area computation for `model_derived` sources (HierText, COCO-Text). Effort: 2 days.

2. **Immediate P0**: Implement synthetic composition script for SUBSTANTIAL class (50–90% handwriting coverage) — overlay handwriting page crops onto printed document backgrounds. Effort: 3 days.

3. **Immediate P0**: Implement handwriting subcommand in `prepare_multitask_datasets.py` following the established script/orientation/shadow pattern. Include NONE class sampling cap (12,000 images) and DOMINANT class sampling cap (12,000 images from ~50K available). Effort: 2 days.

4. **P1 before evaluation**: Source CJK handwriting (CASIA-HWDB or SCUT-HCCDoc), Devanagari handwriting (IIIT-HW), and Cyrillic handwriting (HKR dataset). Add 5,000–10,000 DOMINANT examples per script to unblock the Macro F1 ≥ 0.78 target on non-Latin scripts.

5. **P1 before evaluation**: Add VLM validation gate (Tier 2, 20% sample) for images near the MARGINAL/PARTIAL (10%) and PARTIAL/SUBSTANTIAL (50%) class boundaries to reduce label noise at the most confusion-prone class transitions.
