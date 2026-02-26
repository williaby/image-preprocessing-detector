# Head Adequacy Review: legibility_cls (SIG-G4-2)

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
| Head ID | SIG-G4-2 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | legibility_cls (also written as handwriting_legibility_cls) |
| Task Type | Classification — 6 classes (N_A / ILLEGIBLE / POOR / FAIR / GOOD / EXCELLENT) |
| Output Format | Softmax over 6 legibility levels |
| Priority | P1 |
| Performance Target | Macro F1 >= 0.72 (revised to >= 0.60 per Section 9 consensus — IAA ceiling) |
| Primary L2 Field | `handwriting_assessment.legibility` (6-class enum) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5) — all trained on the same 60K dataset |
| Training Phase | Phase 3 — Handwriting |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.legibility` (6-class enum: N_A / ILLEGIBLE / POOR / FAIR / GOOD / EXCELLENT)

**Confidence Threshold**: >= 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_1_annotation preferred; VLM labeling required for POOR/FAIR/GOOD
distinctions on most sources; heuristic assignment valid for IAM (EXCELLENT) and NONE-presence
images (N_A).

**Dependency**: legibility_cls labels are only meaningful when
`handwriting_assessment.presence` != NONE. All NONE-presence images receive N_A automatically,
creating a clean label dependency on SIG-G4-1.

### Class Definitions

| Class | Description |
| --- | --- |
| N_A | No handwriting present (presence = NONE) — legibility assessment not applicable |
| ILLEGIBLE | Handwriting present but cannot be read by a human expert; unrecoverable |
| POOR | Handwriting very difficult to read; requires significant transcription effort |
| FAIR | Handwriting readable with moderate effort; some characters uncertain |
| GOOD | Handwriting clearly readable with minimal effort; most characters certain |
| EXCELLENT | Handwriting highly legible; near-print quality; zero ambiguity |

### Critical Gap: ILLEGIBLE and POOR Classes

**ILLEGIBLE is entirely absent from all training-eligible datasets.** Curated handwriting
corpora (IAM, Muharaf, PUCIT-OHUL) are systematically biased toward readable samples; inclusion
criteria explicitly filter out unreadable images. Natural scene text datasets (HierText,
COCO-Text) contain degraded text but not handwriting that crosses the threshold of true
illegibility. This is a structural gap, not a data quantity gap.

**POOR class is near-zero** in all current sources. IAM labels every page EXCELLENT by design.
Muharaf and PUCIT-OHUL curate for readability. Only heavily degraded subsets of COCO-Text
(blurred category, ~15% of the dataset) might yield POOR examples after VLM validation.

**Remediation path for ILLEGIBLE**: Two options established by consensus:

1. Source real examples from historical degraded manuscripts (Library of Congress, Internet
   Archive) or medical/prescription writing datasets (~500 images minimum).
2. Synthesize via heavy augmentation (Gaussian blur sigma >= 5, elastic distortion, localized
   shuffle noise) applied to FAIR-class handwriting images to create a proxy ILLEGIBLE class.
   Option 2 is faster but produces synthetic ILLEGIBLE examples that may not generalize to
   real-world illegibility (child handwriting, tremor, extreme compression).

### Candidate Source Datasets

| Dataset | Est. Images | Field Populated | Legibility Coverage | Conf >= 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| IAM Handwriting Database | ~13,000 pages | No — requires derivation | EXCELLENT only (curated by design) | Yes (heuristic: all EXCELLENT) | B+ | Yes — EXCELLENT class only |
| COCO-Text | 63,686 | Partial — 3-class (clear/blurred/others) | clear -> GOOD/EXCELLENT; blurred -> FAIR/POOR; others -> TBD | Partial (3-class, not 6-class) | B | Yes after 6-class mapping |
| HierText | 8,281 | No — binary word-level `legible` field only | Binary aggregated to page-level; maps to GOOD/EXCELLENT only | No | B | Partial — after VLM legibility scoring |
| Muharaf | ~20,000 (GCS-only) | No — no legibility annotations | GOOD to EXCELLENT (curated Arabic handwriting) | No — requires VLM | C (no legibility GT) | After VLM labeling |
| PUCIT-OHUL | ~8,000 (GCS-only) | No — no legibility annotations | FAIR to GOOD (Urdu handwriting, less curated) | No — requires VLM | C (no legibility GT) | After VLM labeling |
| NIST SD-19 | ~814K character images | No — no legibility field | FAIR to GOOD (form entries, varies by writer) | No — requires VLM on page composites | C | After VLM labeling (low priority) |
| FUNSD | 149 pages | No | GOOD (English business forms) | No — small dataset | B | Yes — GOOD class after VLM; too small |
| ILLEGIBLE sources (new) | ~500 target | — | ILLEGIBLE only | — | — | Blocked — not yet acquired |

### Usable Pool Summary

- **N_A class**: Any NONE-presence document from the printed corpus (DocLayNet, RVL-CDIP,
  TableBank) — label is deterministic, no annotation required. ~30K+ images available
  immediately from existing printed datasets.
- **EXCELLENT class**: IAM (~13K pages) — assign heuristically; validate 10% sample via VLM.
- **GOOD/EXCELLENT mixed**: COCO-Text clear subset (~35K), HierText after VLM scoring.
- **FAIR class**: COCO-Text blurred subset (~9.5K), Muharaf after VLM (estimated 15-25% FAIR).
- **POOR class**: COCO-Text blurred tail + PUCIT-OHUL after VLM (estimated 5-10% POOR); severely
  underrepresented even after VLM.
- **ILLEGIBLE class**: 0 — blocked.
- **Training target**: 60,000 images (shared with all G4 heads); legibility-specific subset
  requires all present-handwriting images (~30K if presence split is 50/50).
- **Critical gap**: ILLEGIBLE class must reach >= 500 training examples before assembly can run.

### VLM Validation Sampling Tier

- **IAM**: Tier 2 sample — validate 10% (1,300 images) via VLM to confirm EXCELLENT assumption;
  assign remaining by heuristic.
- **COCO-Text**: Tier 1 targeted — run VLM on 100% of `blurred` and `others` categories
  (~25K images) to assign 6-class labels; apply heuristic GOOD to `clear` category.
- **Muharaf + PUCIT-OHUL**: Tier 1 full — run VLM on 100% (both datasets GCS-only; ~28K
  total); no heuristic assignment available without existing legibility annotations.
- **HierText**: Tier 2 targeted — run VLM on images where word-level legibility ratio is
  between 0.5 and 0.9 (boundary region); apply heuristic GOOD/EXCELLENT outside boundary.

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| HW-LEG-D01 | COCO-Text | legibility | 3-class schema (clear/blurred/others) incompatible with 6-class target — `others` category is undifferentiated mix of scripts, orientations, and quality levels | Open |
| HW-LEG-D02 | IAM | legibility | No legibility field — must be derived; EXCELLENT assumption covers only the best-case scenario; does not generate FAIR/POOR/ILLEGIBLE signal | Open |
| HW-LEG-D03 | Muharaf | legibility | No legibility annotations exist; GCS-only locally; VLM compute cost is non-trivial for 20K Arabic images | Open |
| HW-LEG-D04 | PUCIT-OHUL | legibility | No legibility annotations exist; GCS-only; Urdu script requires VLM with Urdu reading capability | Open |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-02-A | ILLEGIBLE class absent from all training datasets — only covered in OOD-Handwriting 5a (KHATT, 20+ pages) | CRITICAL — zero training examples means zero F1 for this class; Macro F1 target mathematically unachievable |
| KI-G4-02-B | COCO-Text legibility field uses 3-class schema not mappable to 6-class target without VLM | HIGH — mapping required before any FAIR/POOR signal can be extracted |
| KI-G4-02-C | IAM curated dataset assigns EXCELLENT by design — contributes nothing to lower legibility classes | MEDIUM — useful for EXCELLENT class only; does not help class balance |
| KI-G4-02-D | Muharaf and PUCIT-OHUL have no legibility annotations — require full VLM pass for ~28K images | HIGH — significant VLM compute required; GCS-only so cannot be processed locally |
| KI-G4-02-E | IAA for handwriting legibility is 60-70% — ground truth is inherently noisy at class boundaries | HIGH — F1 ceiling ~0.65; affects target achievability and loss function selection |
| KI-G4-02-F | N_A class is categorical (no handwriting), not ordinal — breaks pure ordinal loss function assumption | MEDIUM — standard softmax with label smoothing recommended over ordinal regression |

### Remediation Path

1. Source or synthesize ~500–1,000 ILLEGIBLE training examples (P0).
2. Define and implement COCO-Text 3-class to 6-class mapping rules; run VLM on `blurred`
   and `others` subsets (P0).
3. Run full VLM legibility labeling on Muharaf and PUCIT-OHUL (P1, 2–3 days compute).
4. Validate IAM EXCELLENT assumption via 10% VLM sample (P1, 1 day).
5. Implement handwriting subcommand in `scripts/prepare_multitask_datasets.py` (P0, shared
   blocker with all G4 heads).
6. Revise performance target from Macro F1 >= 0.72 to >= 0.60 to align with IAA ceiling.

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 60,000 images (shared with all G4 heads) |
| Assembly Status | Not started — blocked on ILLEGIBLE class acquisition and VLM legibility labeling |
| Current Count | 0 labeled with `handwriting_assessment.legibility` field |
| ILLEGIBLE Class | P0 blocker — must source 500–1,000 training examples |
| N_A Class | All NONE-presence images receive N_A — deterministic; no annotation required |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Class Distribution Requirements

| Class | Target Coverage | Primary Source | Risk |
| --- | --- | --- | --- |
| N_A | ~50% of training set | Printed negatives (DocLayNet, RVL-CDIP, TableBank) | LOW — easy to source |
| ILLEGIBLE | >= 500 images (absolute minimum) | New acquisition or heavy augmentation of FAIR | CRITICAL — currently 0 examples |
| POOR | >= 5% of handwriting images (~1,500) | COCO-Text blurred tail, PUCIT-OHUL VLM-labeled | HIGH — near-zero in current sources |
| FAIR | >= 15% of handwriting images (~4,500) | COCO-Text blurred, Muharaf/PUCIT-OHUL VLM-labeled | HIGH — requires VLM labeling |
| GOOD | >= 30% of handwriting images (~9,000) | COCO-Text clear, HierText, PUCIT-OHUL VLM-labeled | MEDIUM — dependent on VLM quality |
| EXCELLENT | >= 40% of handwriting images (~12,000) | IAM (heuristic), COCO-Text clear, Muharaf VLM-labeled | LOW — well covered by IAM |

**Blockers**:

- handwriting subcommand of `prepare_multitask_datasets.py` not yet implemented
- ILLEGIBLE class: 0 training examples — must acquire before assembly can begin
- COCO-Text 3-class to 6-class legibility mapping not yet defined or implemented
- VLM legibility labeling for Muharaf (~20K) and PUCIT-OHUL (~8K) not yet run
- L2 field `handwriting_assessment.legibility` unpopulated for all source datasets

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: 0 / 100 (handwriting DDR shows 0 samples loaded — dataset not yet assembled)

**IAA Noise Factor**: All diversity scores are contingent on resolving the label quality
problem. With 60-70% IAA, even a perfectly diverse dataset will have ~30% noisy labels at
class boundaries (FAIR/GOOD, GOOD/EXCELLENT). Label smoothing in training (epsilon = 0.1)
is the recommended mitigation.

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| capture_method | `capture_method.method` | CRITICAL | >= 3 methods (born_digital, scanner, camera) | unknown — 0 samples assembled | 0 |
| domain | `domain.level1` | HIGH | >= 5 domains (business, legal, medical, academic, personal) | unknown | 0 |
| color_mode | `image_properties.color_mode` | MEDIUM | >= 2 modes (color, grayscale) — binarized rare in HW corpora | unknown | 0 |
| document_age | `image_properties.document_age` | HIGH | All 3 ages — historical critical for ILLEGIBLE class sourcing | unknown | 0 |
| script_code | `language.script_code` | HIGH | >= 4 scripts (LATN, ARAB, DEVA, HANS) — currently Latin-only | 1 script (LATN) | 0 |
| resolution | `resolution.category` | MEDIUM | >= 3 tiers (low, medium, high) | unknown | 0 |
| layout_type | `structure.layout_type` | LOW | Mixed page vs. pure handwriting | unknown | 0 |
| degradation | `quality.degradations` | CRITICAL | Blur, noise, contrast (directly drive legibility class) | unknown | 0 |
| handwriting_style | `handwriting_assessment.content_type` | HIGH | All styles per legibility level (cursive, print, mixed) | unknown | 0 |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | unknown | 0 |
| ink_quality | `quality.degradations` (ink_fading) | HIGH | Normal, faded, bleed-through — drives POOR class coverage | unknown | 0 |
| document_type | `domain.document_type` | MEDIUM | >= 4 types (letter, form, note, manuscript) | unknown | 0 |
| mixed_content | `handwriting_assessment.is_mixed` | MEDIUM | Both pure handwriting and mixed (printed + handwritten) pages | unknown | 0 |
| background_complexity | `image_properties.background` | MEDIUM | Plain, lined, printed background — affects legibility perception | unknown | 0 |

**Key diversity gaps identified before assembly**:

- Script diversity is critically absent: current sources cover LATN (IAM, HierText, COCO-Text)
  and ARAB (Muharaf) and URDU/NASTALIO (PUCIT-OHUL). CJK and Devanagari handwriting are
  entirely absent from training — only covered in OOD-Handwriting 5b and 5c.
- Document age: historical handwriting is the most natural source of ILLEGIBLE/POOR classes,
  but zero historical handwriting datasets are in the training pool. If ILLEGIBLE class is
  sourced from historical archives (Library of Congress, Internet Archive), this dimension
  gains coverage simultaneously with class coverage.
- Degradation dimension: ink quality, blur, and bleed-through are directly correlated with
  legibility class. A dataset with no degradation signal cannot train the model to recognize
  why handwriting is illegible (vs. simply classifying by appearance). The IQA degradation
  annotations from Phase 1C could be cross-referenced with handwriting images to enrich this.
- Capture method: IAM is scanner-only; COCO-Text and HierText include camera-captured natural
  scene text. Camera capture introduces glare, perspective distortion, and uneven lighting
  that affects legibility independently of handwriting quality. Missing: born-digital
  handwriting (e.g., digital pen on tablet), which has different characteristics.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 0 / 100 (handwriting DDR wild condition coverage score: 0.0 — dataset not assembled)

**Top concern**: ILLEGIBLE class is the most critical wild condition and is entirely absent
from training. The model will confuse ILLEGIBLE with POOR or N_A at inference time on any
document where handwriting quality drops below the POOR threshold.

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| ILLEGIBLE handwriting (truly unreadable) | `handwriting_assessment.legibility` = ILLEGIBLE | CRITICAL — absent from training | 0 training examples; OOD-only via KHATT 5a (20+ pages) |
| Faded ink (aged documents) | `quality.degradations` incl. ink_fading | Missing | No historical HW dataset in training pool; must source for POOR/ILLEGIBLE classes |
| Bleed-through reducing legibility | `quality.degradations` incl. bleed_through | Missing | Common in thin paper notebooks and pre-1950 documents; absent from all current sources |
| Camera-captured handwriting (glare, uneven lighting) | `capture_method.method` = camera_smartphone | Partial | COCO-Text and HierText have camera-captured text, but not exclusively handwriting pages |
| Dense cursive script (connected letterforms) | `handwriting_assessment.content_type` = cursive | Partial | IAM contains cursive; but IAM is all EXCELLENT, so cursive-FAIR/POOR gap remains |
| Historical letterforms (pre-1900 script conventions) | `image_properties.document_age` = historical | Missing | No historical handwriting in training pool; primary source for POOR/ILLEGIBLE classes |
| Non-Latin cursive scripts (Arabic, Urdu) | `language.script_code` = Arab | Partial | Muharaf (Arabic) in pool but no legibility annotations yet; VLM required |
| Non-Latin scripts CJK and Devanagari | `language.script_code` = Hans/Deva | Missing | Not in training pool — OOD-only (CASIA-HWDB 5b, IIIT-INDIC 5c) |
| Overwriting and corrections on handwritten pages | `quality.degradations` | Missing | Strike-throughs and corrections reduce legibility; not represented in any current source |
| Low-contrast handwriting (pencil, light ink) | `quality.degradations` | Missing | Pencil handwriting common in student notes; none in current sources |
| Handwriting on complex printed backgrounds (forms) | `structure.layout_type` | Partial | FUNSD and NIST-SD2 have form fill-in; very small datasets |
| Medical/prescription writing (notoriously illegible) | — | Missing | No medical handwriting dataset exists in the source pool; primary real-world ILLEGIBLE source |
| Child handwriting (irregular letterforms, poor spacing) | — | Missing | Not represented; common source of POOR classification in real documents |
| Tremor-affected handwriting (organic but difficult) | — | Missing | Not represented; relevant for document processing in healthcare contexts |
| Calligraphic handwriting (legible for experts but unusual) | — | Missing | High legibility for skilled readers but unusual letterforms; model might score FAIR incorrectly |

**Wild condition coverage summary**: 2 partial, 13 missing, 0 fully covered. The dataset is
not assembled, so all scores are structural assessments based on source dataset analysis.
The ILLEGIBLE wild condition is the highest-priority gap because it has no remediation path
within current sources and directly blocks the Macro F1 target.

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | handwriting_presence=SUBSTANTIAL, script=Arab, text_direction=rtl, handwriting_legibility (FAIR/POOR/ILLEGIBLE cases) | SigLIP 2 | Select >= 20 pages with legibility=ILLEGIBLE — only source of ILLEGIBLE-class evaluation data for SIG-G4-2 |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc) | handwriting_presence=DOMINANT, script=HANS/HANT, handwriting_legibility | SigLIP 2 | 2–4 week access request for CASIA; SCUT-HCCDoc open fallback |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset (public access) | handwriting_presence=DOMINANT, script=Deva, text_direction=ltr | SigLIP 2 | Non-Latin script legibility stress — Devanagari legibility scale differs from Latin |
| 5d. Specialized content handwriting | 50 | Mathematical notebooks, engineering drawings — public domain archives | handwriting_content_type=specialized, handwriting_presence | SigLIP 2 | Specialized notation may present unique legibility challenges |

### OOD Acquisition Status

**Status**: Not started (Phase 5, P0)

### OOD Coverage for SIG-G4-2 Specifically

The OOD design for SIG-G4-2 (legibility_cls) has one critical design decision embedded in
sub-source 5a: the model will encounter ILLEGIBLE class examples exclusively at evaluation
time, never during training. This is an open-set test for the ILLEGIBLE class.

**Expected OOD behavior if ILLEGIBLE training gap is not resolved**:

- Model assigns ILLEGIBLE images to POOR or N_A (nearest learned class)
- ILLEGIBLE class F1 = 0.0 at OOD evaluation
- Macro F1 across all classes drops approximately 0.12–0.17 below the training-set score
- OOD evaluation reveals the fundamental gap rather than measuring generalization

**Expected OOD behavior if ILLEGIBLE training gap is resolved (500+ training examples)**:

- Model can activate the ILLEGIBLE logit; recall for this class rises to >0.5 expected
- OOD evaluation measures genuine generalization to unseen ILLEGIBLE cases (KHATT Arabic
  cursive is out-of-distribution even if ILLEGIBLE training examples are English manuscripts)

### Missing OOD Sub-sources

- Additional ILLEGIBLE examples beyond KHATT 20 pages for statistical reliability (need
  minimum 50 ILLEGIBLE evaluation examples for meaningful per-class F1 estimation; 20
  examples yields standard error > 0.07 on F1 estimate).
- POOR legibility examples in non-Arabic scripts — current OOD skews KHATT Arabic for
  lower classes; POOR in CJK or Latin script has no dedicated OOD coverage.

### OOD Leakage Risk

**Level**: MEDIUM

KHATT is not in the training dataset pool. ILLEGIBLE class in OOD is intentionally absent
from training (open-set scenario). Risk arises if KHATT images were inadvertently included
in any training negative pool. SHA256 + pHash dedup required against all training sources
before OOD registration. The COCO-Text overlap risk is MEDIUM: COCO-Text images with
existing `blurred` labels may have been used in training; OOD must not use the same images.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-1 (presence_cls) | legibility_cls depends on presence_cls — N_A legibility applies when presence = NONE | All images with presence=NONE must have legibility=N_A; enforced during assembly; co-training must preserve this invariant |
| SIG-G4-5 (legibility_reg) | legibility_cls is the discretized version of legibility_reg output | Class boundaries must align with score midpoint mapping (ILLEGIBLE: 0.0–0.10; POOR: 0.10–0.30; FAIR: 0.30–0.55; GOOD: 0.55–0.80; EXCELLENT: 0.80–1.00; N_A: sentinel -1.0) |
| SIG-G4-3 (content_type_cls) | Shares training dataset; content_type is orthogonal to legibility | Both heads return N_A when presence=NONE; cursive content_type does not imply lower legibility |
| SIG-G4-4 (presence_reg) | Presence area ratio provides context for legibility interpretation | High presence_reg with low legibility_cls indicates substantial handwriting that is difficult to read — important joint signal for routing decisions |

### Split Leakage Risk

**Level**: MEDIUM

Same global split registry as all G4 heads — SHA256-keyed to prevent same base image
appearing in both train and test. Additional risk specific to SIG-G4-2: COCO-Text images
with `blurred` legibility labels may be in both the handwriting training pool and IQA
training pool. Cross-dataset dedup required between handwriting and IQA assembled datasets
if any COCO-Text images overlap. Stratification must use image SHA256, not legacy label values.

### Label Convention

6-class enum: N_A, ILLEGIBLE, POOR, FAIR, GOOD, EXCELLENT.

- N_A uses underscore notation (consistent with `handwriting_assessment` L2 schema) —
  note the OOD registry schema uses `NOT_APPLICABLE` in some fields; the training manifest
  must normalize to N_A for this head.
- COCO-Text mapping: clear -> GOOD or EXCELLENT (VLM or heuristic GOOD); blurred ->
  FAIR or POOR (VLM required to split); others -> case-by-case VLM.
- IAM heuristic assignment: all pages -> EXCELLENT; validated by 10% VLM sample.
- HierText: aggregate word-level `legible` ratio to page-level; ratio >= 0.90 -> EXCELLENT;
  0.70–0.90 -> GOOD; 0.50–0.70 -> FAIR; < 0.50 -> POOR (apply VLM to boundary regions).

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| HW-LEG-G01 | — | ILLEGIBLE class: 0 training examples — explicit acquisition or synthesis decision required | All curated HW corpora filter out unreadable images by design; structural gap | Option A: Acquire 500 real ILLEGIBLE examples from historical archives or medical datasets; Option B: Synthesize via heavy augmentation (Gaussian blur sigma >= 5, elastic distortion) on FAIR samples; Option B unblocks faster but may not generalize to real ILLEGIBLE | 2 days (Option A acquisition) or 0.5 days (Option B synthesis) |
| HW-LEG-G02 | HW-LEG-D01 | COCO-Text 3-class legibility schema not mapped to 6-class target | Different annotation schemas | Define mapping rules; run VLM on blurred and others subsets (~25K images) | 1 day mapping + 1 day VLM compute |
| HW-LEG-G03 | — | handwriting subcommand of `prepare_multitask_datasets.py` not implemented | Phase 3 dataset prep deprioritized | Implement subcommand (shared blocker with all G4 heads) | 2 days (shared) |
| HW-LEG-G04 | — | L2 field `handwriting_assessment.legibility` unpopulated for all datasets — no label source exists | Labels were never annotated for legibility in source datasets | VLM labeling pipeline required before any training data can be assembled | 3–5 days total VLM compute across all sources |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-LEG-G05 | Muharaf and PUCIT-OHUL: no legibility annotations — FAIR class undercovered without VLM | Datasets collected without legibility scoring | Run VLM legibility labeling on full datasets (~28K images total) | 2–3 days compute |
| HW-LEG-G06 | IAM EXCELLENT assumption needs VLM validation | Assumption not tested | Run VLM on 10% IAM sample (~1,300 images) to confirm assumption; adjust if >5% non-EXCELLENT | 0.5 days |
| HW-LEG-G07 | KHATT OOD provides only 20+ ILLEGIBLE pages — below minimum for reliable per-class F1 estimation (need >= 50) | OOD budget constraint | Expand OOD-Handwriting 5a ILLEGIBLE quota from 20 to 50+ pages; or add supplementary ILLEGIBLE source (e.g., Internet Archive degraded manuscripts) | 0.5 days |
| HW-LEG-G08 | F1 >= 0.72 target exceeds IAA ceiling of 60-70% | IAA noise is structural, not fixable by data | Revise performance target to Macro F1 >= 0.60; alternatively use weighted F1 to allow GOOD/EXCELLENT classes to carry the score | 0 days effort — governance decision |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| HW-LEG-G09 | POOR class underrepresented in Latin-script training data — IAM skews EXCELLENT | Source degraded historical handwriting (Library of Congress scans) or apply ink-fading + noise augmentation to GOOD samples |
| HW-LEG-G10 | Non-Latin legibility (CJK, Devanagari) absent from training — OOD-only via CASIA and IIIT-INDIC | Add CASIA-HWDB subset (~500 images) and IIIT-INDIC subset (~200 images) to training pool |
| HW-LEG-G11 | Legibility IAA not formally measured — class boundary subjectivity unquantified | Double-annotate 200 sample images to measure IAA; adjust FAIR/GOOD boundary definition if kappa < 0.50 |
| HW-LEG-G12 | Loss function selection unresolved — ordinal regression vs. standard softmax | Implement ablation with both (softmax + label smoothing 0.1, vs. coral ordinal loss excluding N_A); choose based on val F1 |

---

## Section 9 — Multi-Model Consensus

**Consensus Run**: 2026-02-23
**Models Consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)
**Confidence**: 9 / 10 (unanimous across both models on core findings)

### Analyst Pre-Consensus Summary

SIG-G4-2 (legibility_cls) faces three compounding problems:

1. **Structural class void**: ILLEGIBLE and POOR classes are absent from all curated training
   sources. This is not a quantity gap — it is a structural gap caused by the systematic
   curation bias of handwriting corpora toward legible samples. No amount of additional
   sampling from the current source pool will provide ILLEGIBLE or POOR examples.
2. **Label quality ceiling**: Legibility is subjective with IAA of 60-70%. This is the
   theoretical performance ceiling for supervised learning. A Macro F1 target of 0.72
   (7 points above the IAA upper bound) is unrealistic regardless of data quantity.
3. **Assembly infrastructure gap**: The `handwriting_assessment.legibility` L2 field is
   unpopulated for every source dataset. The assembly pipeline does not yet have a
   handwriting subcommand. There are no labels to assemble.

The combination of these three factors means the head cannot proceed to training in its
current state.

### Consensus Questions and Findings

**Q1 — ILLEGIBLE class: P0 blocker or valid OOD-only design?**

Both models: **P0 training blocker.** Unanimous at 9/10 confidence.

Rationale: A fixed-size 6-class softmax head cannot activate the ILLEGIBLE logit without
training signal. Without training examples, ILLEGIBLE recall = 0.0. With ILLEGIBLE F1 = 0.0,
achieving Macro F1 >= 0.72 requires avg F1 > 0.86 across the remaining 5 classes — impossible
given IAA noise. Treating ILLEGIBLE as OOD-only is a valid evaluation design but a fatal
training flaw for a supervised classification head.

Divergence: Gemini 2.5 Pro recommends acquiring ~500 real ILLEGIBLE examples. Gemini 3 Pro
Preview recommends synthesizing ILLEGIBLE via heavy augmentation (Gaussian blur + elastic
distortion on FAIR images, N ~500–1,000). Both paths are viable; synthesis is faster to
unblock; real acquisition provides better generalization.

**Recommended approach**: Synthesize ILLEGIBLE training proxy immediately (Option B) to
unblock training schedule; pursue real ILLEGIBLE acquisition in parallel (Option A) for
the next training cycle.

**Q2 — Label derivation for existing datasets**

Both models: Hybrid approach — heuristics for clean assignments, VLM for ambiguous cases.

- IAM: Assign EXCELLENT by heuristic; validate with 10% VLM sample (Gemini 3 Pro recommends
  validation even for IAM due to possible false assumptions).
- COCO-Text: COCO-Text clear -> GOOD (heuristic); COCO-Text blurred and others -> full VLM
  labeling required. Gemini 3 Pro: "Direct mapping from 3-class to 6-class is insufficient."
- Muharaf + PUCIT-OHUL: Full VLM labeling on 100% (~28K images). Both models agree this
  cannot be handled by heuristics.
- VLM scale: Gemini 3 Pro estimates 60K VLM labels costs approximately $200 USD via API,
  which is feasible. Gemini 2.5 Pro recommends targeted VLM to reduce cost; Gemini 3 Pro
  recommends full-pass for data quality consistency.

**Q3 — Ordinal regression vs. standard softmax**

**Key divergence**: Gemini 2.5 Pro recommends ordinal regression (CORAL loss or ordinal
cross-entropy). Gemini 3 Pro Preview (both responses) recommends standard softmax, with the
critical observation that **N_A is categorical and orthogonal** — it represents absence of
the subject being classified (no handwriting), not a quality level below ILLEGIBLE.

Applying CORAL/ordinal loss to the full 6-class schema forces the model to treat N_A as
"worse" than ILLEGIBLE, which has no meaningful semantic interpretation and may degrade
model performance on the N_A boundary.

**Synthesis recommendation**: Use standard softmax cross-entropy with label smoothing
(epsilon = 0.10) to handle IAA boundary noise. The ordinal structure of
ILLEGIBLE < POOR < FAIR < GOOD < EXCELLENT is real, but N_A's categorical nature breaks
pure ordinal regression. If ordinal benefit is desired, apply CORAL loss only to the
5-class quality subset (excluding N_A) and train N_A as a separate binary mask head —
which aligns with the hierarchical relationship between SIG-G4-1 (presence_cls) and
SIG-G4-2 (legibility_cls) already.

**Q4 — F1 >= 0.72 target achievability**

Both models: **Target is unachievable under current conditions and should be revised.**

Arguments:

- IAA ceiling: 60-70% IAA means ~30% of ground truth labels are disputed between human
  annotators. A model cannot reliably exceed human agreement. F1 >= 0.72 implies the model
  must be more consistent than the humans who labeled the data — which typically indicates
  overfitting to annotator-specific biases, not generalization.
- Class void: Missing ILLEGIBLE class alone reduces Macro F1 by approximately 1/6 of any
  achievable score. If the other 5 classes achieve F1 = 0.80, Macro F1 = 0.67 — already
  below target.
- Adjacent-class confusion: FAIR/GOOD boundary has high IAA error rate; POOR/FAIR boundary
  similarly ambiguous. These systematic confusions are not fixable by more data.

Both models recommend revising the target to **Macro F1 >= 0.60**, aligned with the IAA
lower bound. Gemini 3 Pro Preview suggests alternative metric: Mean Absolute Error (MAE)
on the ordinal quality subset (excluding N_A), which penalizes off-by-one errors less than
Macro F1 does — more appropriate for an ordinal task with noisy labels.

**Q5 — Overall adequacy rating**

**Both models: BLOCKED.** Unanimous at 9/10 confidence.

Blocking factors in order of severity:

1. ILLEGIBLE class: 0 training examples (P0)
2. L2 field unpopulated for all sources: no labels exist (P0)
3. Assembly pipeline not implemented: no infrastructure to build the dataset (P0)
4. Performance target unachievable with current design (governance item — not a data blocker
   but must be resolved before evaluation planning)

### Consensus Summary

| Question | Gemini 2.5 Pro | Gemini 3 Pro Preview | Consensus |
| --- | --- | --- | --- |
| ILLEGIBLE class strategy | P0 blocker; acquire real examples | P0 blocker; synthesize via augmentation | P0 blocker; synthesize first, acquire in parallel |
| Label derivation | Hybrid: heuristics first, targeted VLM | Full VLM pass on unlabeled sources | Hybrid — heuristic where safe, full VLM for Muharaf/PUCIT-OHUL |
| Loss function | Ordinal regression (CORAL) | Standard softmax (N_A breaks ordinal) | Softmax + label smoothing; ordinal only if N_A masked separately |
| F1 target | Revise to >= 0.60 | Revise to >= 0.60 or switch to MAE | Revise to Macro F1 >= 0.60 |
| Overall rating | BLOCKED | BLOCKED | BLOCKED |

### Scoring Summary

| Component | Weight | Score | Weighted | Notes |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 15 / 100 | 5.3 | N_A and EXCELLENT well-sourced; ILLEGIBLE = 0; POOR near-zero; FAIR/GOOD require VLM |
| 14-Dimension Coverage | 25% | 10 / 100 | 2.5 | Dataset not assembled; structural gaps in script diversity and degradation dimension |
| Wild Condition Coverage | 20% | 5 / 100 | 1.0 | 2 of 15 conditions partially covered; ILLEGIBLE entirely absent |
| OOD Design Quality | 20% | 60 / 100 | 12.0 | OOD plan is sound; KHATT ILLEGIBLE quota should be expanded to 50+ pages |
| **Overall** | 100% | — | **20.8** | Grade: Blocked |

**Grade**: Blocked — training cannot begin until P0 gaps G01–G04 are resolved.

**Top Recommendations (consensus-derived)**:

1. Synthesize 500–1,000 ILLEGIBLE training examples immediately using heavy augmentation
   on FAIR-class handwriting images to unblock training schedule.
2. Run full VLM legibility labeling on Muharaf (~20K) and PUCIT-OHUL (~8K) as a priority;
   these datasets have no heuristic path to legibility labels.
3. Define and implement COCO-Text 3-class to 6-class legibility mapping; run VLM on
   `blurred` and `others` subsets.
4. Revise performance target from Macro F1 >= 0.72 to >= 0.60 to align with the IAA
   noise ceiling of 60-70%.
5. Expand OOD-Handwriting 5a ILLEGIBLE quota from 20+ to 50+ pages for reliable per-class
   F1 estimation at evaluation time.
6. Use standard softmax + label smoothing (epsilon = 0.10) rather than ordinal regression,
   because N_A is categorical; revisit ordinal loss only if N_A is moved to a hierarchical
   binary pre-filter (aligned with SIG-G4-1 presence_cls dependency).
