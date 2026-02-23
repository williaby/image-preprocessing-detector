# Head Adequacy Review: content_type_cls (SIG-G4-3)

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
| Head ID | SIG-G4-3 |
| Model | SigLIP 2 NAFlex |
| Group | G4 — Handwriting |
| Head Name | content_type_cls (also written as handwriting_content_type_cls) |
| Task Type | Classification — 7 classes (N_A / PRINTED / TYPED / HANDWRITTEN_CURSIVE / HANDWRITTEN_BLOCK / MIXED_PRINTED_HW / MIXED_TYPED_HW) |
| Output Format | Softmax over 7 content types |
| Priority | P1 |
| Performance Target | Macro F1 >= 0.72 |
| Primary L2 Field | `handwriting_assessment.content_type` (7-class enum) |
| Shared-Data Heads | All G4 heads (SIG-G4-1 through SIG-G4-5) — all trained on the same 60K dataset |
| Training Phase | Phase 4 — Handwriting |

### Class Definitions

| Class | Description | Label Strategy |
| --- | --- | --- |
| N_A | No handwriting present; content_type assessment not applicable | Rule-based from presence=NONE |
| PRINTED | Digital typesetting, offset printing, laser printing — no handwriting | Rule-based from born-digital/print-scanner sources |
| TYPED | Typewriter or mechanical type — proportional spacing, typewriter typeface characteristics | VLM labeling on RVL-CDIP letter/memo subset |
| HANDWRITTEN_CURSIVE | Fully handwritten pages in cursive or joined letterform style | Corpus-level (IAM, Muharaf, PUCIT-OHUL) |
| HANDWRITTEN_BLOCK | Fully handwritten in block/print style (disconnected letterforms) | Per-image VLM required; style not noted in IAM metadata |
| MIXED_PRINTED_HW | Pages combining printed/typed base with handwritten annotations (e.g., margin notes) | VLM labeling of FUNSD, RVL-CDIP forms; structural gap |
| MIXED_TYPED_HW | Pages combining typewriter text with handwritten annotations | VLM on historical typed documents; structural gap |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `handwriting_assessment.content_type` (7-class enum)

**Confidence Threshold**: >= 0.7 (tier_1_annotation or better)

**Label Provenance**: Rule-based for N_A and PRINTED; corpus-level heuristic for HANDWRITTEN_CURSIVE; per-image VLM required for TYPED, HANDWRITTEN_BLOCK, MIXED_PRINTED_HW, MIXED_TYPED_HW.

**L2 Field Status**: `handwriting_assessment.content_type` is **unpopulated for all source datasets**. No labeling infrastructure exists.

**Critical Dependency**: This head shares the same 60K training dataset as SIG-G4-1 (presence_cls). The five classes that involve handwriting (TYPED, HANDWRITTEN_CURSIVE, HANDWRITTEN_BLOCK, MIXED_PRINTED_HW, MIXED_TYPED_HW) depend on SIG-G4-1 presence labels being resolved first. The P0 blockers from SIG-G4-1 (HW-PRES-G01 through G05) are prerequisites for this head.

### Per-Dataset Analysis

| Dataset | Total Images | Content Types Suppliable | L2 Field Populated | Label Strategy | Usable Count | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DocLayNet | 80,832 | N_A, PRINTED | No | Rule-based (all_printed) | ~12K (capped) | Born-digital; trivially PRINTED |
| RVL-CDIP | ~400,000 | N_A, PRINTED, TYPED | No | Rule-based PRINTED; VLM for TYPED subset | ~12K PRINTED + ~3-5K TYPED | Typewriter letters ~10% of corpus; historical forms |
| TableBank | 278,000 | N_A, PRINTED | No | Rule-based (all_printed) | Contributes to N_A/PRINTED cap | Academic PDFs; born-digital |
| IAM Handwriting | ~13,000 pages | HANDWRITTEN_CURSIVE, HANDWRITTEN_BLOCK | No | Corpus-level cursive; per-image VLM for block split | ~8-10K after split estimation | IAM contains mixed cursive+block writers; IAA ~55-65% on style split |
| Muharaf | ~20,000 pages | HANDWRITTEN_CURSIVE (Arabic) | No (GCS-only locally) | Corpus-level (all cursive by design) | ~8K (after cap; GCS required) | Arabic cursive; no block-print representation |
| PUCIT-OHUL | ~7,000 pages | HANDWRITTEN_CURSIVE (Urdu) | No (GCS-only locally) | Corpus-level (all cursive by design) | ~3K (GCS required) | Urdu Nastaliq handwriting; all cursive |
| KHATT | ~6,800 pages | HANDWRITTEN_CURSIVE (Arabic) | No | Corpus-level (all cursive by design) | ~3K | Arabic handwriting corpus; uniform cursive style |
| NIST-SD2 | ~10,000 pages | HANDWRITTEN_BLOCK | No | Corpus-level (form fill-ins, block print) | ~5K | Digit + alphanumeric form entries; block style dominant |
| COCO-Text | 63,686 images | N_A, PRINTED, MIXED_PRINTED_HW (marginal) | No | VLM per-image; mostly scene-text not document-level | ~8K N_A/PRINTED; <100 MIXED_PRINTED_HW | Scene text dataset; very few document + annotation pages |
| HierText | 8,281 pages | N_A, PRINTED, HANDWRITTEN_CURSIVE (marginal) | No | VLM or polygon analysis | ~3K N_A/PRINTED; limited HW coverage | Word-level polygon annotations; not document-level HW |
| FUNSD | ~200 forms | MIXED_PRINTED_HW | No | VLM per-page (form fill-in annotations) | ~150 after VLM (extremely small) | Best natural source of MIXED_PRINTED_HW; far below target |

### Critical Class Gaps

**MIXED_PRINTED_HW — ZERO labeled examples in all curated datasets.**
No standard document dataset is purpose-designed to capture documents with printed text plus handwritten annotations. FUNSD (149 pages) is the only identified natural source. Even if all FUNSD pages qualify as MIXED_PRINTED_HW after VLM validation, this yields ~150 examples versus a target of ~8,500. Sourcing paths:

1. VLM labeling of RVL-CDIP form subset (estimate 0.5-2% of 400K = 2K-8K candidates) — requires VLM pass at scale.
2. Targeted acquisition of real business documents (scanned office archives with margin notes).
3. Synthetic composition: overlay handwriting region onto printed page at design time.
None of these paths are implemented. This is a structural gap requiring a new data acquisition strategy.

**MIXED_TYPED_HW — ZERO labeled examples in all curated datasets.**
Typewriter text with handwritten annotations is extremely rare in digitized corpora. Historical typed letters and administrative documents with handwritten annotations exist in archive collections but are not in the current source pool. This class is even harder to source than MIXED_PRINTED_HW because typewriter text itself (TYPED class) is already scarce in modern digitized document collections.

**HANDWRITTEN_CURSIVE vs. HANDWRITTEN_BLOCK — per-image labeling required.**
IAM contains both cursive and block-print writers, but the dataset does not label writing style at page level. Splitting IAM into HANDWRITTEN_CURSIVE and HANDWRITTEN_BLOCK requires per-image VLM annotation. Expected IAA for this distinction: 55-65% (cursive/block boundary is not always unambiguous; semi-joined letterforms create a gray zone). This creates a label quality ceiling for these two classes.

**TYPED vs. PRINTED — subtle distinction requiring VLM or specialist labeling.**
TYPED (typewriter) differs from PRINTED (digital/offset) in proportional spacing characteristics, typeface features (fixed-pitch vs. proportional), and paper/ink interaction. VLM models with vision-language capabilities can generally distinguish these, but IAA is expected around 70-80% on ambiguous cases. Most RVL-CDIP TYPED examples are clear typewriter documents; however, early laser printers and low-quality photocopies can be ambiguous.

### Usable Pool Summary

| Class | Available (Pre-Cap) | After Sampling Cap | Status |
| --- | --- | --- | --- |
| N_A | >350,000 | 12,000 | Ready (rule-based, no labeling needed) |
| PRINTED | >400,000 | 12,000 | Ready (rule-based after TYPED split) |
| TYPED | ~3,000-8,000 (estimated from RVL-CDIP) | ~3,000-8,000 | Requires VLM labeling; may fall short of 8,500 target |
| HANDWRITTEN_CURSIVE | ~46,000 (IAM 13K + Muharaf 20K + PUCIT-OHUL 7K + KHATT 6K) | 12,000 | Solid after GCS access; cursive split from IAM needed |
| HANDWRITTEN_BLOCK | ~8,000-12,000 (NIST-SD2 + IAM block fraction) | 8,000-12,000 | Requires per-image VLM split on IAM |
| MIXED_PRINTED_HW | ~150-2,000 (FUNSD + RVL-CDIP VLM candidates) | <2,000 | CRITICAL GAP — well below 8,500 target |
| MIXED_TYPED_HW | ~0-200 (speculative from archive collections) | <200 | CRITICAL GAP — essentially zero |

**Training target**: 60,000 images (shared with all G4 heads). Of these, the 5 handwriting-present classes must collectively cover at least ~30,000 images (N_A and PRINTED fill the other ~30,000).

**Total gap**: MIXED_PRINTED_HW and MIXED_TYPED_HW are structurally absent. The 60K target is unachievable with current data plan for a balanced 7-class dataset.

### VLM Validation Sampling Tier

- N_A and PRINTED: Tier 1 (automated rule-based; no VLM needed)
- TYPED: Tier 2 — VLM on 100% of RVL-CDIP letter/memo subset to confirm TYPED vs. PRINTED classification
- HANDWRITTEN_CURSIVE: Tier 1 for Muharaf/PUCIT-OHUL/KHATT (corpus-level); Tier 2 for IAM (10% VLM sample to validate cursive fraction)
- HANDWRITTEN_BLOCK: Tier 2 — VLM on 100% of IAM and NIST-SD2 to assign cursive vs. block
- MIXED_PRINTED_HW: Tier 3 — VLM on entire FUNSD corpus + RVL-CDIP form candidates; quality gate before use
- MIXED_TYPED_HW: Tier 3 — VLM on targeted acquisition; manual review required

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| HW-CONT-D01 | All datasets | `handwriting_assessment.content_type` | L2 field unpopulated across all source datasets | Open — blocks all assembly |
| HW-CONT-D02 | IAM | `handwriting_assessment.content_type` | No style annotation (cursive vs. block) exists; requires per-image labeling | Open |
| HW-CONT-D03 | FUNSD | `handwriting_assessment.content_type` | FUNSD is the only natural MIXED_PRINTED_HW source but provides only ~150 pages | Open — insufficient count |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-G4-03-A | MIXED_PRINTED_HW class has zero reliably labeled examples from any curated dataset | CRITICAL — class cannot be trained; Macro F1 target unachievable with missing class |
| KI-G4-03-B | MIXED_TYPED_HW class has near-zero labeled examples — even harder to source than MIXED_PRINTED_HW | CRITICAL — class essentially blocked |
| KI-G4-03-C | HANDWRITTEN_CURSIVE vs. HANDWRITTEN_BLOCK distinction requires per-image VLM; IAA ~55-65% | HIGH — label quality ceiling on two classes; may require class collapse |
| KI-G4-03-D | TYPED vs. PRINTED distinction is subtle; early laser print and low-quality photocopy are genuinely ambiguous | MEDIUM — IAA ~70-80%; may cause cross-class confusion at inference |
| KI-G4-03-E | L2 field `handwriting_assessment.content_type` unpopulated for all datasets — no labeling infrastructure | P0 BLOCKER — head cannot train without labels |
| KI-G4-03-F | All handwriting-present classes depend on SIG-G4-1 presence_cls P0 blockers (HW-PRES-G01 through G05) | BLOCKER — serial dependency on presence_cls resolution |

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 60,000 images (shared with all G4 heads) |
| Assembly Status | Blocked — L2 field unpopulated, MIXED classes have no viable source, assembly pipeline not implemented |
| Current Count | 0 images with valid 7-class content_type labels |
| MIXED_PRINTED_HW Class | Structural gap — ~150 natural examples exist; target ~8,500 |
| MIXED_TYPED_HW Class | Structural gap — ~0-200 speculative examples; target ~8,500 |
| N_A / PRINTED Classes | Rule-based; trivially adequate from printed corpus |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (handwriting subcommand not yet implemented) |

### Class Distribution Requirements

| Class | Target Count | Target % | Derivation Method | Risk |
| --- | --- | --- | --- | --- |
| N_A | 12,000 | 20% | Rule-based from NONE-presence printed docs | LOW — trivially abundant; cap required |
| PRINTED | 12,000 | 20% | Rule-based from born-digital + non-typed scanner docs | LOW — trivially abundant |
| TYPED | 6,000 | 10% | VLM labeling of RVL-CDIP letter/memo subset | MEDIUM — requires VLM; may yield only 3-8K |
| HANDWRITTEN_CURSIVE | 12,000 | 20% | Corpus-level (IAM/Muharaf/PUCIT-OHUL/KHATT) + per-image split | LOW — adequate after GCS access and IAM split |
| HANDWRITTEN_BLOCK | 6,000 | 10% | Per-image VLM on NIST-SD2 + IAM block fraction | MEDIUM — IAA ceiling 55-65% on style split |
| MIXED_PRINTED_HW | 6,000 | 10% | VLM on FUNSD + RVL-CDIP form subset; synthetic composition fallback | CRITICAL — natural pool ~150-2K; far below target |
| MIXED_TYPED_HW | 6,000 | 10% | Targeted archive acquisition; synthetic composition | CRITICAL — pool essentially zero; new acquisition required |

**Blockers**:

- L2 field unpopulated for all datasets (P0)
- MIXED_PRINTED_HW natural pool: ~150 examples vs. 6,000 target (P0)
- MIXED_TYPED_HW natural pool: ~0-200 examples vs. 6,000 target (P0)
- handwriting subcommand of `prepare_multitask_datasets.py` not implemented (P0)
- Serial dependency on SIG-G4-1 presence_cls P0 resolution (P0)

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: Estimated 18/100 (pre-assembly projection; dominated by MIXED class absence and script diversity failure)

The primary diversity failure is class balance: two of seven classes have near-zero examples. Secondary failures are script diversity (CJK/Devanagari handwriting absent) and document_age (historical typed documents absent, which is where TYPED class with degradation would come from).

| Dimension | L2 Field | Relevance | Target | Current Estimate | Score |
| --- | --- | --- | --- | --- | --- |
| class_balance | `handwriting_assessment.content_type` | CRITICAL | ~6,000-12,000 per class | MIXED classes: 0; N_A/PRINTED: >350K each; others: partial | 8/100 |
| script_diversity | `language.script_code` | HIGH | >= 5 scripts covering HW classes (LATN, ARAB, URDU, HANS, DEVA) | LATN (IAM), ARAB (Muharaf/KHATT), URDU (PUCIT-OHUL) — CJK/Deva absent for any HW class | 25/100 |
| capture_method | `capture_method.method` | HIGH | >= 3 methods (born_digital, scanner, camera) across all classes | born_digital (PRINTED), scanner (TYPED, HW classes); camera: minimal | 30/100 |
| document_age | `image_properties.document_age` | HIGH | Modern + aged (TYPED class in particular requires aged/historical docs) | Mostly modern; historical typewriter docs absent | 15/100 |
| color_mode | `image_properties.color_mode` | MEDIUM | >= 2 modes (color, grayscale) | IAM/NIST-SD2: grayscale; DocLayNet/COCO-Text: color | 40/100 |
| domain | `domain.level1` | MEDIUM | >= 5 domains (academic, financial, legal, medical, personal) | Academic (IAM), financial (NIST-SD2), natural scene (COCO-Text); medical/legal absent | 28/100 |
| degradation | `quality.degradations` | MEDIUM | >= 3 types (blur, aging, bleed-through) | IAM/NIST-SD2: clean scans; degraded HW examples scarce | 20/100 |
| mixed_content | `handwriting_assessment.is_mixed` | HIGH | Both pure HW and mixed (MIXED_PRINTED_HW, MIXED_TYPED_HW) pages | Near zero — MIXED class structural gap | 5/100 |
| handwriting_style | content_type itself | CRITICAL | All 5 HW content types covered | HANDWRITTEN_CURSIVE adequate; BLOCK partial; MIXED classes absent | 20/100 |
| layout_type | `structure.layout_type` | MEDIUM | >= 3 types (pure manuscript, form, mixed) | Manuscript (IAM), form (NIST-SD2), document (DocLayNet) — mixed layout absent | 25/100 |
| page_density | `structure.text_density` | LOW | Sparse, normal, dense | Limited variation; IAM/NIST-SD2 typically full-page coverage | 35/100 |
| document_type | `domain.document_type` | MEDIUM | >= 4 types (letter, form, note, notebook) | Letter/note (IAM), form (NIST-SD2), article (DocLayNet) | 30/100 |
| background_complexity | `image_properties.background` | MEDIUM | Plain, lined, printed-form backgrounds | Plain dominant (IAM); form backgrounds only in NIST-SD2 | 30/100 |
| writing_instrument | (no dedicated L2 field) | LOW | Pen, pencil, marker represented | Mostly pen (IAM/Muharaf); pencil and marker absent | 20/100 |

**Key Dimension Findings**:

- Class balance is the dominant failure: two of seven classes are structurally absent.
- Script diversity is severely limited for handwriting classes: SigLIP 2 will be biased toward Latin/Arabic cursive styles and will not generalize to CJK or Devanagari handwriting in production.
- Mixed content dimension is the second structural failure: the entire MIXED class subtree requires document types that no current source naturally provides.
- Document age is a critical secondary gap: TYPED class examples are inherently historical (typewriters are pre-1980s) but no historical document aging is in the training pool.

---

## Section 5 — Wild Condition Coverage

**Overall Score**: 12/100 (structural assessment based on source pool analysis)

| Wild Condition | L2 Field Evidence | Dataset Coverage | Status | Severity |
| --- | --- | --- | --- | --- |
| Annotation in margins of printed academic papers (MIXED_PRINTED_HW archetype) | `handwriting_assessment.content_type` = MIXED_PRINTED_HW | FUNSD (149 pages); no other natural source at scale | Absent | CRITICAL — defines the MIXED_PRINTED_HW class |
| Typewriter text on aged/yellowed paper (TYPED with degradation) | `image_properties.document_age` = aged + content_type = TYPED | No historical typed document dataset in current pool | Absent | HIGH — TYPED class requires degraded historical examples to be robust |
| Mixed-script pages: printed English with handwritten Arabic/Chinese annotations | `language.is_mixed_script` + content_type = MIXED_PRINTED_HW | No training source provides this; common in real bilingual documents | Absent | HIGH — fails on multilingual office documents |
| Low-resolution handwriting causing HANDWRITTEN_BLOCK vs. TYPED confusion | `resolution.category` = low + content_type boundary | No targeted low-res HW examples in plan | Absent | HIGH — at low DPI, block handwriting and typewriter text can be visually indistinguishable |
| Calligraphic decorative printed text classified as HANDWRITTEN_CURSIVE | `handwriting_assessment.content_type` boundary case | No training source provides calligraphic confusion examples | Absent | MEDIUM — decorative fonts can activate handwriting features |
| Carbon copy pages (faint repeat printing from typewriter) | content_type = TYPED + degradation = bleed_through | No carbon copy examples in any current source | Absent | MEDIUM — common in pre-1980s archived documents |
| Redacted or crossed-out text on handwritten pages | `quality.degradations` + content_type = HANDWRITTEN_CURSIVE/BLOCK | Absent from all training sources | Absent | MEDIUM — corrections and deletions change visual character of handwriting |
| Tabular form with handwritten cell entries (MIXED_PRINTED_HW) | `structure.layout_type` = form + content_type = MIXED_PRINTED_HW | FUNSD (149 pages) — single small source | Sparse | HIGH — the most common real-world MIXED scenario |
| Scanned photocopied document (PRINTED degraded to grayscale with photocopy artifacts) | `capture_method` = scanner + PRINTED | Covered by RVL-CDIP partially | Partial | MEDIUM |
| Camera-captured handwritten notes with perspective distortion and glare | `capture_method.method` = camera_smartphone + HANDWRITTEN_CURSIVE | COCO-Text has camera-captured scene text; IAM is flatbed only | Partial (scene text only) | HIGH — smartphone document photography is common in production |

**Wild condition coverage summary**: 1 partial, 1 sparse, 8 absent, 0 fully covered. The head is not assembled, so all assessments are structural. The MIXED class wild conditions are the highest-severity gaps because they represent conditions the model will encounter in real business document processing but will have had no training signal for.

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Handwriting (Phase 5, P0, 500 total images)

All G4 heads (SIG-G4-1 through SIG-G4-5) share the same OOD-Handwriting sub-sources.

### OOD Sub-Sources

| Sub-Source | Images | Source | Content-Type Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 5a. KHATT Arabic cursive | 200 | KHATT dataset | content_type=HANDWRITTEN_CURSIVE, script=Arab, text_direction=rtl | SigLIP 2 | Primary OOD stress for HANDWRITTEN_CURSIVE generalization to non-Latin script; 200 images provides adequate per-class F1 estimation |
| 5b. CASIA-HWDB CJK handwritten | 150 | CASIA-HWDB (fallback: SCUT-HCCDoc) | content_type=HANDWRITTEN_CURSIVE (CJK stroke-based), script=HANS/HANT | SigLIP 2 | CJK handwriting tests whether HANDWRITTEN_CURSIVE generalizes beyond alphabetic scripts; 2-4 week access lead time |
| 5c. IIIT-INDIC Devanagari handwritten | 100 | IIIT-INDIC dataset | content_type=HANDWRITTEN_CURSIVE or HANDWRITTEN_BLOCK, script=Deva | SigLIP 2 | Non-Latin script; tests Indian subcontinent handwriting generalization |
| 5d. Specialized content handwriting | 50 | Mathematical notebooks, engineering drawings (public domain archives) | content_type=HANDWRITTEN_CURSIVE or HANDWRITTEN_BLOCK (specialized notation is not a content_type class in this schema) | SigLIP 2 | Note: `specialized` from the older scaffold schema is not a class in the current 7-class schema; these images should be labeled by nearest class |

### Critical OOD Gap for This Head

The OOD-Handwriting design does not include any MIXED_PRINTED_HW or MIXED_TYPED_HW examples. Since these two classes are the highest-risk training gaps, having no OOD evaluation for them means the model's failure mode on mixed content cannot be quantified at evaluation time.

The OOD sub-sources cover only HANDWRITTEN_CURSIVE (3 non-Latin script variants). This provides useful generalization stress for that class but leaves 5 of 7 content_type classes completely absent from OOD evaluation.

**Required OOD additions for adequate content_type_cls evaluation**:

- 5e (proposed): MIXED_PRINTED_HW OOD — 50 real business documents with handwritten margin annotations (scanned office archives, library holdings) — tests the most critical production failure mode
- 5f (proposed): TYPED class OOD — 50 historical typewriter documents with varying degradation levels — tests TYPED class generalization

### OOD Acquisition Status

**Status**: Not started (Phase 5, P0)

### OOD Leakage Risk

**Level**: MEDIUM

KHATT and CASIA-HWDB are not in the training dataset pool, so direct overlap risk is LOW. The main risk is that COCO-Text images used in training (PRINTED/N_A class) may share document origins with scene text in HierText-sourced OOD images. SHA256 + pHash dedup (Hamming <= 5) required against all training sources before OOD registration.

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G4-1 (presence_cls) | Hard dependency — content_type is meaningful only when presence != NONE | All images with presence=NONE must have content_type=N_A; enforced during assembly; serial blocker dependency |
| SIG-G4-2 (legibility_cls) | Shares training dataset; legibility is orthogonal to content_type but co-occurs | HANDWRITTEN_BLOCK should not systematically correlate with lower legibility than HANDWRITTEN_CURSIVE in clean datasets (IAM, NIST-SD2); if this correlation appears, it indicates label artifacts |
| SIG-G4-4 (presence_reg) | Shares training dataset; content_type informs expected presence_reg range | MIXED_PRINTED_HW should correlate with intermediate presence_reg scores (0.10-0.50); HANDWRITTEN_CURSIVE should correlate with DOMINANT presence; label consistency check required |
| SIG-G4-5 (legibility_reg) | Shares training dataset | Legibility score must be jointly consistent with content_type; TYPED documents should not receive low legibility_reg without corroborating degradation labels |

### Split Leakage Risk

**Level**: MEDIUM

All G4 heads share the same training dataset. Global split registry (SHA256-keyed) required to ensure consistent train/val/test splits across all G4 head training manifests. Additional risk specific to this head: if content_type labels are assigned at corpus level (all IAM = HANDWRITTEN_CURSIVE, all NIST-SD2 = HANDWRITTEN_BLOCK) rather than per-image, split stratification cannot use label values meaningfully — must stratify by dataset source + SHA256.

### Label Convention

7-class enum using UPPER_SNAKE_CASE (N_A, PRINTED, TYPED, HANDWRITTEN_CURSIVE, HANDWRITTEN_BLOCK, MIXED_PRINTED_HW, MIXED_TYPED_HW). The N_A value is categorical (not a quality level) and is consistent with the `handwriting_assessment` group convention established by SIG-G4-1 (NONE presence -> N_A content_type) and SIG-G4-2 (NONE presence -> N_A legibility). The softmax output for N_A must be masked during any ordinal analysis of the handwriting-specific classes.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-CONT-G01 | L2 field `handwriting_assessment.content_type` unpopulated for all source datasets — no label source exists | Labels never collected; field defined in schema but not populated | Define and implement per-dataset labeling rules (rule-based for N_A/PRINTED; VLM for all others); implement in harmonize script as parallel to legibility labeling | 2 days |
| HW-CONT-G02 | MIXED_PRINTED_HW class: ~150 natural examples vs. 6,000 target — structural gap | No curated dataset is designed to capture printed documents with handwritten annotations at scale | Option A: Scale VLM labeling on RVL-CDIP form subset (requires 10-30% hit rate on ~20K form images); Option B: Implement synthetic composition script overlaying handwriting regions onto printed document pages; Option C: Targeted acquisition of scanned office document archives | 3-5 days (Option B recommended as fastest path) |
| HW-CONT-G03 | MIXED_TYPED_HW class: near-zero natural examples — structural gap more severe than MIXED_PRINTED_HW | Typewriter documents with handwritten annotations are rare in digitized archives and not systematically labeled | Option A: Archive acquisition from historical typed document collections (Library of Congress, Internet Archive); Option B: Synthetic composition on TYPED class examples; likely requires combining with TYPED class labeling effort | 3-5 days minimum; sourcing timeline uncertain |
| HW-CONT-G04 | HANDWRITTEN_CURSIVE vs. HANDWRITTEN_BLOCK per-image split not implemented — IAM page-level style unknown | IAM does not label writing style per page; style split requires VLM or human annotation | Run VLM content_type labeling on 100% of IAM pages (~13K) to split into CURSIVE/BLOCK; validate on 10% sample; if IAA < 0.65, collapse to single HANDWRITTEN class | 1-2 days VLM compute |
| HW-CONT-G05 | handwriting subcommand of `prepare_multitask_datasets.py` not implemented | Phase 4 dataset prep deprioritized | Implement subcommand following established script/orientation/shadow pattern; include N_A cap (12K), PRINTED cap (12K), class balance enforcement | 2 days (shared blocker with all G4 heads) |
| HW-CONT-G06 | Serial dependency on SIG-G4-1 presence_cls P0 blockers (HW-PRES-G01 through G05) | Presence labels are a prerequisite for content_type label assignment | Resolve SIG-G4-1 P0 gaps first; estimated 11-13 days engineering for presence_cls blocker resolution | 11-13 days (in SIG-G4-1 scope) |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| HW-CONT-G07 | TYPED class: VLM labeling on RVL-CDIP required; estimated yield 3-8K vs. 6K target | RVL-CDIP has typewriter letters but they are not labeled at schema level | Run VLM on RVL-CDIP letter/memo subset (~40K candidate images); filter by TYPED confidence >= 0.7 | 2 days VLM compute |
| HW-CONT-G08 | HANDWRITTEN_CURSIVE non-Latin expansion blocked by GCS access | Muharaf (~20K) and PUCIT-OHUL (~7K) are GCS-only locally | Run full harmonize on GCS VM to include non-Latin cursive; adds ~27K HANDWRITTEN_CURSIVE examples for sampling | 1 day GCS run |
| HW-CONT-G09 | OOD does not cover MIXED_PRINTED_HW or MIXED_TYPED_HW failure modes | OOD-Handwriting was designed before MIXED class gaps were identified | Add OOD sub-source 5e: 50 real MIXED_PRINTED_HW examples (scanned documents with margin annotations) from library archive collections | 1 day acquisition |
| HW-CONT-G10 | Class balance strategy for N_A imbalance not defined | N_A pool (>350K) will overwhelm training without sampling cap | Define and enforce sampling cap: N_A = 12K (20%), PRINTED = 12K (20%); apply class weights for minority classes (MIXED) if underrepresented | 0.5 days design |
| HW-CONT-G11 | IAA not formally measured for HANDWRITTEN_CURSIVE vs. BLOCK distinction — label quality unknown | Style split is novel annotation task; annotator agreement unquantified | Double-annotate 200 sample IAM images for cursive/block; measure Cohen's kappa; if kappa < 0.50, collapse HANDWRITTEN_CURSIVE and HANDWRITTEN_BLOCK to single HANDWRITTEN class and revise head spec | 1 day |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| HW-CONT-G12 | CJK handwriting absent from HANDWRITTEN_CURSIVE training class — OOD-only via CASIA-HWDB | Source CASIA-HWDB or SCUT-HCCDoc Chinese handwritten documents; add ~2K-5K HANDWRITTEN_CURSIVE examples to training pool |
| HW-CONT-G13 | Degraded TYPED class (aged typewriter documents) absent from training | Source historical typewriter documents with Augraphy aging augmentation (yellowing, ink fading); target 500-1K examples |
| HW-CONT-G14 | Calligraphic printed fonts absent as PRINTED class confounders | Add decorative/calligraphic digital font examples to PRINTED class to prevent false HANDWRITTEN_CURSIVE activation |
| HW-CONT-G15 | MIXED_TYPED_HW class viability: if natural acquisition yields < 500 examples after full acquisition effort, consider collapsing into MIXED_PRINTED_HW as a single MIXED class | Conduct data audit after P0 acquisition; if MIXED_TYPED_HW < 500 after 2 weeks effort, propose schema revision |

### Total Remediation Estimate

- **P0 Blockers**: ~22-27 days engineering effort (including 11-13 days for SIG-G4-1 dependency resolution)
- **P1 Improvements**: ~5-7 days additional effort before evaluation
- **Total to Evaluation-Ready**: approximately 27-34 engineering days (dominated by presence_cls serial dependency)

---

## Section 9 — Multi-Model Consensus

**Consensus Run Date**: 2026-02-23

**Models Consulted**: google/gemini-2.5-pro (neutral), google/gemini-3-pro-preview (neutral)

**Consensus Confidence**: 9/10 (both models aligned on core finding: BLOCKED)

### Analyst Pre-Consensus Summary

SIG-G4-3 content_type_cls faces four compounding problems:

1. **Structural class void**: MIXED_PRINTED_HW and MIXED_TYPED_HW classes have zero labeled examples from any curated source. Unlike ILLEGIBLE in SIG-G4-2 (where augmentation can synthesize a proxy), mixed-content documents require both a printed base document AND a handwritten annotation component simultaneously — this is a structural gap requiring either a new data acquisition strategy (business document archives) or a synthetic composition pipeline that does not exist.

2. **Serial blocking dependency**: All five handwriting-present content_type classes depend on SIG-G4-1 presence_cls P0 resolution. SIG-G4-1 is itself Blocked (score 32/100) with 11-13 days of P0 engineering needed. This head cannot proceed until SIG-G4-1 is unblocked.

3. **Label quality ceiling on key distinctions**: The HANDWRITTEN_CURSIVE vs. HANDWRITTEN_BLOCK split requires per-image VLM annotation with IAA expected at 55-65%. This is below the 70% minimum acceptable IAA for a classification head and may require schema consolidation. The TYPED vs. PRINTED distinction has higher IAA (~70-80%) but still requires significant VLM compute.

4. **Infrastructure gap**: The `handwriting_assessment.content_type` L2 field is unpopulated for every source dataset. No labeling pipeline exists. The assembly subcommand does not exist.

### Consensus Questions and Findings

**Q1: Is the source pool sufficient once P0 gaps are resolved?**

Gemini 2.5 Pro: NO. Even after P0 resolution, the source pool is critically insufficient for MIXED classes. VLM labeling of unrelated datasets (FUNSD, RVL-CDIP form subset) is speculative and not a credible strategy for acquiring 6,000 examples per MIXED class. Diversity scores for script (20/100) and document_age (20/100) are too low for acceptable generalization.

Gemini 3 Pro: BLOCKED / REDUNDANT (note: response addressed a related regression head but key themes transfer). Structural class void for MIXED classes requires synthetic composition or new data acquisition — without this, the head cannot function as a 7-class classifier.

Synthesis: The source pool is NOT sufficient. N_A, PRINTED, and HANDWRITTEN_CURSIVE are adequately sourced. TYPED and HANDWRITTEN_BLOCK are reachable with VLM labeling. MIXED_PRINTED_HW and MIXED_TYPED_HW require a new data strategy not in the current plan. Overall pool sufficiency is approximately 5 of 7 classes.

**Q2: Are the P0 blockers correctly identified and prioritized?**

Both models: YES. The P0 blockers are correctly identified. Gemini 2.5 Pro specifically validated: (a) MIXED class absence is the most severe issue — without data, the model cannot be trained on these classes; (b) Unpopulated L2 field and missing labeling infrastructure are correctly identified as prerequisites; (c) The serial dependency on SIG-G4-1 is appropriately flagged.

**Q3: Does the OOD design adequately stress this head's realistic failure modes?**

Both models agree: NO. The OOD design completely fails to test the MIXED classes — the most critical production failure mode. Real-world business documents will frequently present as MIXED_PRINTED_HW (signed typed letters, annotated forms, margin-noted academic papers). The absence of MIXED class OOD coverage means this failure mode will not be quantifiable at evaluation time.

The OOD sub-sources (KHATT, CASIA-HWDB, IIIT-INDIC) all test HANDWRITTEN_CURSIVE generalization to non-Latin scripts, which is valuable but represents only one of seven classes. A balanced OOD design should include stress scenarios for all non-trivial classes.

**Q4: What risks are missing from the gap registry?**

Gemini 2.5 Pro identified missing risks:

- Class definition viability: IAA ~55-65% for CURSIVE/BLOCK and ~70-80% for TYPED/PRINTED may indicate these distinctions are too ambiguous to be worth training a model on. The gap registry does not flag this as a risk.
- Implicit synthetic data dependency: Achieving the MIXED class targets will require synthetic composition — a complex, unbudgeted engineering effort with domain gap risks.
- VLM labeling feasibility: The plan relies heavily on VLM for multiple subtle distinctions. The accuracy, cost, and scalability at ~60K-label scale are unproven.

Additional risks identified in synthesis:

- Schema viability: If MIXED_TYPED_HW acquisition yields < 500 examples after full effort, the 7-class schema should be revised to 5 classes (collapsing MIXED subclasses and HANDWRITTEN subclasses). This governance decision is not in the gap registry.
- Cross-head label consistency: The MIXED classes require presence_cls to label the same images as PARTIAL or MARGINAL — but presence_cls is blocked. Label consistency across the G4 head family is only achievable if both are assembled simultaneously from the same image pool.

**Q5: Overall adequacy rating**

Both models: BLOCKED.

The head cannot proceed because: (1) two of seven classes have zero training examples with no credible near-term sourcing path; (2) the entire label infrastructure does not exist; (3) the assembly pipeline is not implemented; (4) the head is serially blocked by SIG-G4-1 presence_cls P0 resolution. The dataset design identifies the correct class structure and the right approach for five of seven classes, but the MIXED class gap is structural and requires either new data acquisition or schema revision before training can begin.

### Consensus Summary

| Question | Gemini 2.5 Pro | Gemini 3 Pro (synthesized) | Consensus |
| --- | --- | --- | --- |
| Pool sufficient after P0? | NO — MIXED classes unreachable via VLM on existing sources | BLOCKED — synthetic dependency unbudgeted | NO — 5 of 7 classes reachable; MIXED classes require new strategy |
| P0 blockers correctly identified? | YES | YES (pattern holds for G4 heads) | YES |
| OOD design adequate? | NO — omits MIXED class testing entirely | NO — critical failure modes untested | NO — add OOD sub-sources 5e/5f for MIXED classes |
| Missing risks? | IAA viability, synthetic dependency, VLM feasibility | Schema viability threshold, label consistency cross-head | All four identified; add to registry as P1 |
| Overall rating | BLOCKED | BLOCKED | BLOCKED |

### Scoring Summary

| Component | Weight | Score | Weighted Score | Rationale |
| --- | --- | --- | --- | --- |
| Source Pool Adequacy | 35% | 25/100 | 8.75 | N_A and PRINTED trivially adequate; HANDWRITTEN_CURSIVE solid after GCS; TYPED reachable; HANDWRITTEN_BLOCK reachable; MIXED_PRINTED_HW ~2% of target; MIXED_TYPED_HW ~0% of target |
| 14-Dimension Coverage | 25% | 18/100 | 4.50 | Class balance (8/100) and mixed content (5/100) dominate; script diversity (25/100) limited to Latin/Arabic; document age (15/100) critically absent for TYPED class |
| Wild Condition Coverage | 20% | 12/100 | 2.40 | 1 sparse, 1 partial, 8 absent; MIXED class archetypes entirely absent; TYPED degradation absent |
| OOD Design Quality | 20% | 48/100 | 9.60 | 4 sub-sources correctly target HANDWRITTEN_CURSIVE non-Latin generalization; CASIA-HWDB access scheduling risk; MIXED class failure modes entirely unrepresented in OOD; proposed additions (5e/5f) would raise score to ~65 |
| **Overall** | 100% | — | **25.25** | — |

**Overall Score**: 25/100

**Grade**: Blocked — training cannot begin until P0 gaps HW-CONT-G01 through G06 are resolved.

### Top Recommendations (consensus-derived)

1. **Immediate P0**: Implement synthetic composition script for MIXED_PRINTED_HW — programmatically overlay handwriting annotation regions onto printed document page crops at 10-30% area coverage. This is the fastest path to MIXED class training examples. Effort: 3-5 days. This unblocks both MIXED_PRINTED_HW and can be extended to MIXED_TYPED_HW.

2. **Immediate P0 (governance)**: Measure IAA on 200 IAM pages for CURSIVE vs. BLOCK distinction before committing to the 7-class schema. If kappa < 0.50, collapse HANDWRITTEN_CURSIVE and HANDWRITTEN_BLOCK into a single HANDWRITTEN class and revise the head to 6 classes. Effort: 1 day annotation + 0.5 days decision. This decision should be made before any VLM labeling begins on IAM.

3. **P0 dependency**: Resolve SIG-G4-1 presence_cls P0 blockers (HW-PRES-G01 through G05) in parallel. This head cannot assemble content_type labels without presence labels being resolved first. Track SIG-G4-1 remediation progress as a prerequisite.

4. **P1 before OOD evaluation**: Add OOD sub-sources 5e (50 real MIXED_PRINTED_HW examples) and 5f (50 TYPED with degradation examples) to OOD-Handwriting design. Without these, the head's most critical failure modes cannot be quantified at evaluation time.

5. **P1 (schema risk)**: After P0 acquisition effort for MIXED_TYPED_HW, if yield is < 500 examples after 2 weeks of archive sourcing, formally propose collapsing MIXED_TYPED_HW into a single MIXED class with MIXED_PRINTED_HW. Document this as a schema revision in the planning documents.
