---
owner: docs-team
purpose: Cross-reference grid mapping all 79 source datasets to the 22 training heads across
  MobileNetV4-Conv-S and SigLIP 2 NAFlex models. Derived by aggregating Section 13 from each
  dataset source file.
schema_type: common
status: complete
tags:
- datasets
- training
- coverage
title: Dataset ↔ Training Head Coverage Reference
---

> **Version**: 1.0.0
> **Last Updated**: 2026-02-26
> **Source of Truth**: Individual dataset Section 13 entries in `docs/datasets/source/*.md`
> **Do not edit manually** — update by running the aggregation agent after batch analysis is complete.

---

## Navigation

- [Section 1: Head Requirements Digest](#1-head-requirements-digest)
- [Section 2: Cross-Reference Grid](#2-cross-reference-grid)
- [Section 3: Per-Dataset Summaries](#3-per-dataset-summaries)

---

## 1. Head Requirements Digest

> Concise reference for all 22 training heads. Use this when assigning datasets during analysis.
>
> **Critical disambiguations**:
>
> - `skew_reg` (MNV4-H2, SIG-G3-2) = geometric angle in degrees — requires angle-labeled images
> - `skew_score` (SIG-G1-4) = quality degradation 0-1 — NOT the same as angle
> - `code_cls` (SIG-G5-4) = binary sigmoid+BCE; output threshold 0.5; NOT regression
> - Handwriting N/A labels = -1.0 with masked_loss=true (NOT 0.0)
> - Reserved OOD scripts (NEVER in training): Mongolian (Mong), Syriac (Syrc), Georgian (Geor)

### MobileNetV4-Conv-S — Pre-Correction Gate (3 heads)

| Head ID | Head Name | Task | Min Samples | Synthetic Cap | Real:Synth | Label Tier | Key Constraint |
| ------- | --------- | ---- | ----------- | ------------- | ---------- | ---------- | -------------- |
| MNV4-H1 | orientation_cls | 4-class softmax {0°,90°,180°,270°} | 50,000 | ≤40% | ≥60% real | tier_0_exact | Accuracy target ≥95% |
| MNV4-H2 | skew_reg | Regression ±10° angle (degrees) | 90,000 | ≤37.5% | ≥62.5% real | tier_0_exact + tier_2_model | MAE < 0.5°, SRCC > 0.93 |
| MNV4-H3 | resolution_quality_reg | Regression 0-1 (char-height-aware) | 30,000 | ≤17% | ≥83% real | tier_0_exact + tier_3_heuristic | MAE < 0.1 within-bucket |

### SigLIP 2 Group 1 — IQA (6 regression heads, ~125K shared dataset)

| Head ID | Head Name | Task | Min Samples | Synthetic Cap | Label Tier | Key Constraint |
| ------- | --------- | ---- | ----------- | ------------- | ---------- | -------------- |
| SIG-G1-1 | blur_score | Regression 0-1 severity | ~25K hard + 100K pseudo | Phase 2 ≤50% | tier_1_annot + tier_2_model | VQualA ≥ 0.92 |
| SIG-G1-2 | noise_score | Regression 0-1 severity | Same ~125K | — | tier_1_annot + tier_2_model | VQualA ≥ 0.92 |
| SIG-G1-3 | contrast_score | Regression 0-1 severity | Same ~125K | — | tier_1_annot + tier_2_model | VQualA ≥ 0.92 |
| SIG-G1-4 | skew_score | Regression 0-1 quality degradation | Same ~125K | — | tier_1_annot + tier_2_model | VQualA ≥ 0.92; NOT geometric angle |
| SIG-G1-5 | compression_score | Regression 0-1 JPEG impact | Same ~125K | — | tier_1_annot + tier_2_model | VQualA ≥ 0.92 |
| SIG-G1-6 | overall_quality | Regression 0-1 perceptual | Same ~125K | — | tier_1_annot | VQualA ≥ 0.92; SRCC ≥ 0.65 vs MOS |

### SigLIP 2 Group 2 — Script Detection (1 head)

| Head ID | Head Name | Task | Min Samples | Synthetic Cap | Label Tier | Key Constraint |
| ------- | --------- | ---- | ----------- | ------------- | ---------- | -------------- |
| SIG-G2-1 | script_cls | 19-class ISO 15924 | 108,000 balanced | ≤60% | tier_0_exact + tier_1_annot | ≥90% overall; Tibetan ≥80%; Mong/Syrc/Geor excluded |

### SigLIP 2 Group 3 — Post-Correction Orientation + Skew (2 heads)

| Head ID | Head Name | Task | Min Samples | Synthetic Cap | Label Tier | Key Constraint |
| ------- | --------- | ---- | ----------- | ------------- | ---------- | -------------- |
| SIG-G3-1 | orientation_cls (post) | 4-class softmax (post-correction) | 50,000 | ≤40% | tier_0_exact | ≥98% accuracy; same images as MNV4-H1 |
| SIG-G3-2 | skew_reg (post) | Regression ±2° residual | ~20,000 | — | tier_0_exact | MAE < 0.3°; filtered from main 90K skew set (abs(angle)≤2°, conf≥0.8) |

### SigLIP 2 Group 4 — Handwriting Assessment (5 heads, 60K shared)

| Head ID | Head Name | Task | Classes | Min Samples | Label Tier | Key Constraint |
| ------- | --------- | ---- | ------- | ----------- | ---------- | -------------- |
| SIG-G4-1 | handwriting_presence_cls | 5-class | NONE/SPARSE/MODERATE/SUBSTANTIAL/DOMINANT | 60,000 | tier_1_annot + tier_3_heuristic | ≥88%; distribution 35/15/20/15/15% |
| SIG-G4-2 | handwriting_legibility_cls | 6-class | NOT_APPLICABLE/EXCELLENT/GOOD/FAIR/POOR/ILLEGIBLE | Same | — | ≥85%; N/A label=-1.0 masked |
| SIG-G4-3 | handwriting_content_type_cls | 7-class | not_applicable/signatures/numeric/alphanumeric/prose/mixed/specialized | Same | — | specialized ≥500 samples |
| SIG-G4-4 | presence_reg | Regression 0-1 (area ratio) | — | Same | — | MAE < 0.15 |
| SIG-G4-5 | legibility_reg | Regression 0-1 (readability) | — | Same | — | MAE < 0.15 |

### SigLIP 2 Group 5 — Page Attributes (5 heads)

| Head ID | Head Name | Task | Min Samples | Synthetic Cap | Label Tier | Key Constraint |
| ------- | --------- | ---- | ----------- | ------------- | ---------- | -------------- |
| SIG-G5-1 | capture_method_cls | 7-class: BORN_DIGITAL/SCANNER_FLATBED/SCANNER_ADF/CAMERA_PROFESSIONAL/CAMERA_SMARTPHONE/FAX/SYNTHETIC | 50,000 | 0% (all real) | tier_1_annot + tier_3_heuristic | ≥85% accuracy |
| SIG-G5-2 | shadow_reg | Regression 0-1 severity | ~18,000 | ≤50% | tier_0_exact + real_paired | MAE < 0.08 |
| SIG-G5-3 | warping_reg | Regression 0-1 severity | ~24,000 | ≤30% | tier_0_exact + real_paired | MAE < 0.08 |
| SIG-G5-4 | code_cls | Binary sigmoid+BCE (has_code) | 10,000 | ~50% | tier_0_exact + tier_1_annot | Precision > 0.8 @ threshold 0.5 |
| SIG-G5-5 | resolution_quality_reg | Regression 0-1 (char-height; redundant with MNV4-H3) | ~30,000 | ≤17% | tier_0_exact + tier_3_heuristic | MAE within 0.05 of MNV4-H3 |

---

## 2. Cross-Reference Grid

> **Legend**: ✅ Primary contributor | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### Grid A: MobileNetV4 Heads (3 heads)

| Dataset | MNV4-H1 orientation_cls | MNV4-H2 skew_reg | MNV4-H3 resolution_quality_reg |
| ------- | ----------------------- | ---------------- | ------------------------------- |
| anyphotodoc6300 | ❌ | ❌ | ❌ |
| arabic-docs | 🟡 | 🟡 | 🟡 |
| bhutan-afs | ✅ | ➖ | ✅ |
| casia-hwdb2 | ➖ | ➖ | 🟡 |
| casia-hwdb2-line | ❌ | ❌ | ❌ |
| cc-ocr | ➖ | ➖ | 🟡 |
| cocotext | ➖ | ❌ | 🟡 |
| cvsi | ➖ | ➖ | 🟡 |
| dibco | ❌ | ❌ | ❌ |
| diqa-5000 | ❌ | ❌ | ❌ |
| doc3d | ❌ | ❌ | ❌ |
| docalign12k | ❌ | ❌ | ❌ |
| doclaynet | ➖ | ➖ | 🟡 |
| docreal | ❌ | ❌ | 🟡 |
| docsynth | 🟡 | ➖ | 🟡 |
| egyptian-handwriting | ❌ | ❌ | 🟡 |
| document-haystack | ❌ | ❌ | ❌ |
| drccbi | ❌ | ❌ | 🟡 |
| dzongkha-digits | ❌ | ❌ | ❌ |
| financebench | ❌ | ❌ | ❌ |
| fintabnet | ➖ | ➖ | 🟡 |
| funsd | 🟡 | 🟡 | 🟡 |
| funsd-plus | 🟡 | 🟡 | 🟡 |
| gnhk | ➖ | ➖ | 🟡 |
| hasy | ❌ | ❌ | ❌ |
| hiertext | ➖ | ➖ | 🟡 |
| hindi-synth | ➖ | ➖ | 🟡 |
| iam | 🟡 | 🟡 | 🟡 |
| iiit-hw-hindi | ❌ | ❌ | ➖ |
| im2latex | ➖ | ➖ | 🟡 |
| indicdlp | 🟡 | 🟡 | 🟡 |
| invoices-kg | ✅ | ❌ | 🟡 |
| jssoda | ✅ | ➖ | ➖ |
| khatt | ❌ | ❌ | ❌ |
| kleister-charity | ❌ | ❌ | ❌ |
| kuzushiji | ❌ | ❌ | ➖ |
| markushgrapher | ❌ | ❌ | 🟡 |
| mathverse | ❌ | ❌ | ❌ |
| mdiw13 | ➖ | ➖ | ➖ |
| mle2e | 🟡 | 🟡 | 🟡 |
| midv2020 | ✅ | ❌ | ❌ |
| midv500 | ➖ | ❌ | ❌ |
| mlt19 | 🟡 | ❌ | ➖ |
| muharaf | ❌ | ❌ | 🟡 |
| nara-1950-census | ❌ | 🟡 | ❌ |
| multimodal-textbook | 🟡 | ➖ | 🟡 |
| multilingual-scripts | 🟡 | 🟡 | 🟡 |
| ndl-docl | 🟡 | 🟡 | 🟡 |
| ndl-minhon | ❌ | ❌ | ➖ |
| nepali-handwritten | 🟡 | 🟡 | ❌ |
| nist-sd19 | 🟡 | 🟡 | 🟡 |
| nist-sd2 | ➖ | ➖ | 🟡 |
| nist-sd6 | 🟡 | 🟡 | 🟡 |
| ocr-quality | ❌ | ❌ | 🟡 |
| openpecha-ocr-drutsa | ➖ | ➖ | 🟡 |
| ohr-bench | ❌ | ❌ | ❌ |
| omnidocbench | ➖ | ❌ | ➖ |
| openlid-v2 | ❌ | ❌ | ❌ |
| pdmocr-part1 | 🟡 | 🟡 | 🟡 |
| pdmocr-part2 | 🟡 | 🟡 | 🟡 |
| popp-line | ➖ | ➖ | 🟡 |
| pubtabnet | ➖ | ➖ | ➖ |
| pucit-ohul | 🟡 | 🟡 | ❌ |
| q-doc | ❌ | ❌ | 🟡 |
| realdae | 🟡 | ❌ | 🟡 |
| rvl-cdip | ✅ | 🟡 | 🟡 |
| salami | ❌ | ❌ | 🟡 |
| sd7k | 🟡 | ❌ | ❌ |
| signatr6k | ➖ | ❌ | 🟡 |
| signverod | ➖ | ➖ | 🟡 |
| siw13 | ➖ | ➖ | 🟡 |
| smartdoc-qa | ❌ | ❌ | ❌ |
| sroie | ✅ | 🟡 | 🟡 |
| staindoc | ❌ | ❌ | 🟡 |
| tablebank | ➖ | ➖ | 🟡 |
| tibhcr | 🟡 | ❌ | ❌ |
| tobacco800 | ➖ | ➖ | 🟡 |
| vjroda | 🟡 | ➖ | 🟡 |
| warpdoc | 🟡 | ❌ | ❌ |
| wili-2018 | ❌ | ❌ | ❌ |
| wsrd | 🟡 | ❌ | ❌ |
| yarmouk | 🟡 | 🟡 | 🟡 |

### Grid B: SigLIP 2 Group 1 — IQA (6 heads)

| Dataset | G1-1 blur | G1-2 noise | G1-3 contrast | G1-4 skew_score | G1-5 compression | G1-6 overall_quality |
| ------- | --------- | ---------- | ------------- | --------------- | ---------------- | -------------------- |
| anyphotodoc6300 | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| arabic-docs | ✅ | ✅ | ✅ | 🟡 | 🟡 | ✅ |
| bhutan-afs | ➖ | ➖ | ✅ | ➖ | ➖ | ✅ |
| casia-hwdb2 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| casia-hwdb2-line | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| cc-ocr | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| cocotext | 🟡 | 🟡 | 🟡 | ❌ | 🟡 | ❌ |
| cvsi | ✅ | 🟡 | 🟡 | ➖ | ✅ | 🟡 |
| dibco | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| diqa-5000 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| doc3d | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| docalign12k | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 |
| doclaynet | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| docreal | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| docsynth | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| egyptian-handwriting | 🟡 | ❌ | 🟡 | ❌ | ❌ | 🟡 |
| document-haystack | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| drccbi | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| dzongkha-digits | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| financebench | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| fintabnet | ➖ | ➖ | 🟡 | ➖ | 🟡 | 🟡 |
| funsd | ✅ | ✅ | ✅ | 🟡 | 🟡 | ✅ |
| funsd-plus | ✅ | ✅ | ✅ | 🟡 | 🟡 | ✅ |
| gnhk | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| hasy | ➖ | ➖ | ❌ | ❌ | ❌ | ❌ |
| hiertext | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| hindi-synth | 🟡 | 🟡 | 🟡 | ➖ | ❌ | 🟡 |
| iam | 🟡 | 🟡 | 🟡 | 🟡 | ➖ | 🟡 |
| iiit-hw-hindi | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| im2latex | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| indicdlp | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| invoices-kg | ➖ | ➖ | 🟡 | ❌ | 🟡 | 🟡 |
| jssoda | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| khatt | 🟡 | 🟡 | 🟡 | ❌ | 🟡 | 🟡 |
| kleister-charity | 🟡 | 🟡 | 🟡 | 🟡 | ❌ | ❌ |
| kuzushiji | ➖ | ➖ | ➖ | ❌ | ➖ | ❌ |
| markushgrapher | 🟡 | 🟡 | 🟡 | ❌ | 🟡 | 🟡 |
| mathverse | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| mdiw13 | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| mle2e | ✅ | ✅ | ✅ | 🟡 | ✅ | 🟡 |
| midv2020 | 🟡 | 🟡 | ✅ | ❌ | ✅ | ✅ |
| midv500 | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| mlt19 | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| muharaf | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| nara-1950-census | 🟡 | ➖ | 🟡 | ❌ | ➖ | 🟡 |
| multimodal-textbook | 🟡 | 🟡 | 🟡 | ➖ | ✅ | 🟡 |
| multilingual-scripts | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| ndl-docl | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| ndl-minhon | 🟡 | 🟡 | 🟡 | ❌ | ➖ | ❌ |
| nepali-handwritten | 🟡 | 🟡 | 🟡 | 🟡 | ➖ | ❌ |
| nist-sd19 | 🟡 | 🟡 | ➖ | 🟡 | ❌ | 🟡 |
| nist-sd2 | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| nist-sd6 | 🟡 | 🟡 | ➖ | 🟡 | ❌ | 🟡 |
| ocr-quality | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| openpecha-ocr-drutsa | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| ohr-bench | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| omnidocbench | ➖ | ➖ | ➖ | ❌ | ➖ | ➖ |
| openlid-v2 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| pdmocr-part1 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| pdmocr-part2 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| popp-line | 🟡 | 🟡 | 🟡 | ❌ | 🟡 | 🟡 |
| pubtabnet | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ |
| pucit-ohul | ➖ | ➖ | ➖ | ➖ | ➖ | ❌ |
| q-doc | 🟡 | 🟡 | 🟡 | ❌ | ❌ | ✅ |
| realdae | 🟡 | 🟡 | 🟡 | ❌ | ❌ | ❌ |
| rvl-cdip | 🟡 | ✅ | 🟡 | 🟡 | 🟡 | ✅ |
| salami | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| sd7k | ➖ | 🟡 | ✅ | ❌ | ❌ | 🟡 |
| signatr6k | 🟡 | 🟡 | 🟡 | ❌ | ❌ | ❌ |
| signverod | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| siw13 | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| smartdoc-qa | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| sroie | ✅ | ✅ | ✅ | 🟡 | ✅ | ✅ |
| staindoc | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| tablebank | 🟡 | 🟡 | 🟡 | ➖ | 🟡 | 🟡 |
| tibhcr | ➖ | ➖ | ➖ | ❌ | ➖ | ❌ |
| tobacco800 | 🟡 | 🟡 | 🟡 | ➖ | ❌ | 🟡 |
| vjroda | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| warpdoc | 🟡 | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| wili-2018 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| wsrd | ➖ | 🟡 | ✅ | ❌ | ❌ | 🟡 |
| yarmouk | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |

### Grid C: SigLIP 2 Group 2 — Script (1 head)

| Dataset | G2-1 script_cls |
| ------- | --------------- |
| anyphotodoc6300 | ➖ |
| arabic-docs | ✅ |
| bhutan-afs | ✅ |
| casia-hwdb2 | ✅ |
| casia-hwdb2-line | ✅ |
| cc-ocr | ✅ |
| cocotext | 🟡 |
| cvsi | ✅ |
| dibco | ❌ |
| diqa-5000 | ❌ |
| doc3d | ❌ |
| docalign12k | ❌ |
| doclaynet | 🟡 |
| docreal | 🟡 |
| docsynth | 🟡 |
| document-haystack | ❌ |
| egyptian-handwriting | ✅ |
| drccbi | ❌ |
| dzongkha-digits | 🟡 |
| financebench | ❌ |
| fintabnet | ✅ |
| funsd | ✅ |
| funsd-plus | ✅ |
| gnhk | ✅ |
| hasy | ❌ |
| hiertext | ✅ |
| hindi-synth | ✅ |
| iam | 🟡 |
| iiit-hw-hindi | 🟡 |
| im2latex | 🟡 |
| indicdlp | ✅ |
| invoices-kg | ✅ |
| jssoda | ✅ |
| khatt | 🟡 |
| kleister-charity | 🟡 |
| kuzushiji | ✅ |
| markushgrapher | ❌ |
| mathverse | ❌ |
| mdiw13 | ✅ |
| mle2e | ✅ |
| midv2020 | ✅ |
| midv500 | ✅ |
| mlt19 | ✅ |
| muharaf | ✅ |
| nara-1950-census | ✅ |
| multimodal-textbook | ✅ |
| multilingual-scripts | ✅ |
| ndl-docl | ✅ |
| ndl-minhon | ✅ |
| nepali-handwritten | ✅ |
| nist-sd19 | ✅ |
| nist-sd2 | 🟡 |
| nist-sd6 | ✅ |
| ocr-quality | 🟡 |
| ohr-bench | ❌ |
| omnidocbench | 🟡 |
| openpecha-ocr-drutsa | ✅ |
| openlid-v2 | ❌ |
| pdmocr-part1 | ✅ |
| pdmocr-part2 | ✅ |
| popp-line | ✅ |
| pubtabnet | 🟡 |
| pucit-ohul | ✅ |
| q-doc | ❌ |
| realdae | 🟡 |
| rvl-cdip | 🟡 |
| salami | ✅ |
| sd7k | ➖ |
| signatr6k | ➖ |
| signverod | ✅ |
| siw13 | ✅ |
| smartdoc-qa | ❌ |
| sroie | ✅ |
| staindoc | ❌ |
| tablebank | 🟡 |
| tibhcr | ✅ |
| tobacco800 | ➖ |
| vjroda | ✅ |
| warpdoc | ➖ |
| wili-2018 | ❌ |
| wsrd | ➖ |
| yarmouk | ✅ |

### Grid D: SigLIP 2 Groups 3–5 (12 heads)

| Dataset | G3-1 orient_post | G3-2 skew_post | G4-1 hw_presence | G4-2 hw_legibility | G4-3 hw_content | G4-4 presence_reg | G4-5 legibility_reg | G5-1 capture | G5-2 shadow | G5-3 warping | G5-4 code | G5-5 res_qual |
| ------- | ---------------- | -------------- | ---------------- | ------------------ | --------------- | ----------------- | ------------------- | ------------ | ----------- | ------------ | --------- | ------------- |
| anyphotodoc6300 | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ✅ | ❌ | ❌ |
| arabic-docs | 🟡 | 🟡 | ✅ | 🟡 | 🟡 | ✅ | 🟡 | ✅ | 🟡 | 🟡 | ❌ | 🟡 |
| bhutan-afs | ✅ | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ➖ | ➖ | ➖ | ✅ |
| casia-hwdb2 | ➖ | ➖ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| casia-hwdb2-line | ❌ | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | ❌ |
| cc-ocr | ➖ | ➖ | ✅ | ❌ | ❌ | ✅ | ❌ | ➖ | ➖ | ➖ | 🟡 | 🟡 |
| cocotext | ➖ | ❌ | ✅ | ✅ | ➖ | 🟡 | 🟡 | ✅ | ❌ | ❌ | ➖ | 🟡 |
| cvsi | ➖ | ➖ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | 🟡 | ➖ | ✅ | 🟡 |
| dibco | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| diqa-5000 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| doc3d | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ➖ | ❌ | ✅ | ❌ | ❌ |
| docalign12k | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ✅ | ❌ | ❌ |
| doclaynet | ➖ | ➖ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ➖ | ➖ | 🟡 | 🟡 |
| docreal | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ✅ | ➖ | 🟡 |
| docsynth | 🟡 | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 🟡 | 🟡 |
| document-haystack | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| egyptian-handwriting | ❌ | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| drccbi | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ✅ | ❌ | 🟡 |
| dzongkha-digits | ❌ | ❌ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ❌ | ❌ | ❌ | ❌ |
| financebench | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| fintabnet | ➖ | ➖ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ➖ | ➖ | ➖ | 🟡 |
| funsd | 🟡 | 🟡 | ✅ | 🟡 | 🟡 | ✅ | 🟡 | ✅ | 🟡 | ➖ | ➖ | 🟡 |
| funsd-plus | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ✅ | 🟡 | ➖ | ➖ | 🟡 |
| gnhk | ➖ | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 🟡 |
| hasy | ❌ | ❌ | 🟡 | 🟡 | ✅ | ➖ | 🟡 | 🟡 | ❌ | ❌ | ❌ | ❌ |
| hiertext | ➖ | ➖ | ✅ | ✅ | 🟡 | ✅ | ✅ | ✅ | 🟡 | ➖ | 🟡 | 🟡 |
| hindi-synth | ➖ | ➖ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 |
| iam | 🟡 | 🟡 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ➖ | ➖ | ➖ | 🟡 |
| iiit-hw-hindi | ❌ | ❌ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ➖ | ❌ | ❌ | ❌ | ➖ |
| im2latex | ➖ | ➖ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | 🟡 |
| indicdlp | 🟡 | 🟡 | ✅ | ➖ | ➖ | 🟡 | ❌ | ✅ | ❌ | ❌ | 🟡 | 🟡 |
| invoices-kg | ✅ | ❌ | ➖ | ➖ | ➖ | ➖ | ➖ | ✅ | ➖ | ➖ | ❌ | 🟡 |
| jssoda | ✅ | ➖ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ➖ |
| khatt | ❌ | ❌ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ❌ | ❌ | ❌ | ❌ |
| kleister-charity | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 🟡 |
| kuzushiji | ❌ | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | 🟡 | ❌ | ❌ | ❌ | ➖ |
| markushgrapher | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 |
| mathverse | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| mdiw13 | ➖ | ➖ | 🟡 | ❌ | ❌ | 🟡 | ❌ | ✅ | ❌ | ❌ | ❌ | ➖ |
| mle2e | 🟡 | 🟡 | ➖ | ➖ | ➖ | ➖ | ➖ | ✅ | 🟡 | 🟡 | ❌ | 🟡 |
| midv2020 | ✅ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ❌ | ❌ | ❌ |
| midv500 | ➖ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ❌ | ❌ | ❌ |
| mlt19 | 🟡 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ➖ | ➖ | ❌ | ➖ |
| muharaf | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| nara-1950-census | ❌ | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | ❌ |
| multimodal-textbook | 🟡 | ➖ | ✅ | ✅ | ✅ | 🟡 | ➖ | ✅ | ➖ | ➖ | 🟡 | 🟡 |
| multilingual-scripts | 🟡 | 🟡 | ✅ | ❌ | ❌ | ✅ | ❌ | ➖ | ➖ | ➖ | ❌ | 🟡 |
| ndl-docl | 🟡 | 🟡 | ✅ | 🟡 | 🟡 | ✅ | 🟡 | ✅ | 🟡 | ❌ | ❌ | 🟡 |
| ndl-minhon | ✅ | ➖ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | ❌ | ❌ | 🟡 |
| nepali-handwritten | 🟡 | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | 🟡 | 🟡 | ❌ | ❌ |
| nist-sd19 | 🟡 | 🟡 | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| nist-sd2 | ➖ | ➖ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ➖ | ➖ | ➖ | 🟡 |
| nist-sd6 | 🟡 | 🟡 | ✅ | ✅ | ✅ | 🟡 | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| ocr-quality | ❌ | ❌ | ➖ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 |
| openpecha-ocr-drutsa | ➖ | ➖ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ❌ | ❌ | ❌ | 🟡 |
| ohr-bench | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| omnidocbench | ➖ | ❌ | 🟡 | ❌ | ❌ | ❌ | ❌ | ➖ | ❌ | ❌ | 🟡 | ➖ |
| openlid-v2 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| pdmocr-part1 | 🟡 | 🟡 | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | 🟡 | ❌ | ❌ | 🟡 |
| pdmocr-part2 | 🟡 | 🟡 | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | 🟡 | ❌ | ❌ | 🟡 |
| popp-line | ➖ | ➖ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| pubtabnet | ➖ | ➖ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ➖ | ➖ | ➖ | ➖ |
| pucit-ohul | 🟡 | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | ❌ |
| q-doc | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | 🟡 | 🟡 | 🟡 | ➖ | ✅ |
| realdae | 🟡 | ❌ | ➖ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | 🟡 | ➖ | 🟡 |
| rvl-cdip | ✅ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| salami | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 🟡 |
| sd7k | 🟡 | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| signatr6k | ➖ | ❌ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| signverod | ➖ | ➖ | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| siw13 | ➖ | ➖ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | 🟡 | ➖ | ✅ | 🟡 |
| smartdoc-qa | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| sroie | ✅ | 🟡 | 🟡 | ➖ | ➖ | 🟡 | ➖ | ✅ | 🟡 | 🟡 | ❌ | 🟡 |
| staindoc | ❌ | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | 🟡 | ➖ | ❌ | 🟡 |
| tablebank | ➖ | ➖ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ➖ | ➖ | 🟡 | 🟡 |
| tibhcr | 🟡 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| tobacco800 | ➖ | ➖ | ✅ | 🟡 | 🟡 | 🟡 | 🟡 | ✅ | ❌ | ❌ | ❌ | 🟡 |
| vjroda | 🟡 | ➖ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 🟡 |
| warpdoc | 🟡 | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| wili-2018 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| wsrd | 🟡 | ❌ | ➖ | ❌ | ❌ | ➖ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| yarmouk | 🟡 | 🟡 | ✅ | 🟡 | ✅ | ✅ | 🟡 | ✅ | ➖ | ➖ | ✅ | 🟡 |

---

## 3. Per-Dataset Summaries

### anyphotodoc6300

AnyPhotoDoc6300 is the **primary source for `warping_reg` head training**, providing 3,153+ real camera-captured warped documents with flat GT pairs that enable SSIM-derived severity scoring (warping severity 0–1 must be computed from image pair comparison before training). It is also a significant contributor to `capture_method_cls` (~3.1K camera images) and IQA heads (contrast/blur from 3 lighting conditions × 3 warping patterns × 8 layout categories). Warping severity labels are not provided natively and must be pre-computed via `scripts/label_warping_severity.py`. The GPL-3.0 applies to the associated code repository; the dataset terms should be verified separately before commercial deployment.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No official split defined |
| Val   | — | No val split defined |
| Test  | Unknown | No official split defined |
| OOD   | — | Single undivided pool of 6,306 images |

**Ground Truth**: Paired image structure (warped input + flat/rectified GT); annotation method is Paired GT (Tier 0 Exact), with flat images serving as dewarping targets — no manual human annotation required.

**L2 Metadata**: Available — 6,306 total samples. Key fields: domain (SCI 28.5%, UNK 20.6%, FIN 19.1%), script_codes (Latn 51.4%, Hans 43.5%, Hant 2.6%, Jpan 2.6%), capture_methods (camera_smartphone 100%), content_flags (has_figure 52.3%, has_formula 42.8%, has_table 19.1%, has_handwriting 14.3%).

### arabic-docs

Arabic-docs is a **primary contributor for Arabic script detection (SIG-G2-1)** and **handwriting presence detection (SIG-G4-1)** via its labeled "Handwritten text" category, and a **primary contributor for scanner capture-method classification (SIG-G5-1)** since it is the only dataset with 100% confirmed scanner labels at scale. The CC-BY-4.0 license permits commercial use with attribution. The dataset's domain_level1=UNK across all samples (Grade D audit cap) prevents domain-stratified sampling; enrichment to populate this field is required before advancing beyond Grade D.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No official split defined in source |
| Val   | — | No val split defined |
| Test  | Unknown | No official split defined in source |
| OOD   | — | Single-pool, 10,045 images across 12 categories |

**Ground Truth**: Document-type labels are 100% ground truth derived from folder structure (12 categories); approximately 69% of images have human-annotated Arabic title transcriptions via Supervisely JSON, with the remainder having bounding boxes only (no text transcription). Provenance tier is mixed Tier 1 (human titles) and Tier 2 (automatic OCR extraction).

**L2 Metadata**: Not yet available.

### bhutan-afs

Bhutan-AFS serves as the **only real-document-level Tibetan (Tibt) script source** in the training corpus, bridging the gap between tibhcr's character-level images and real-world multi-page Tibetan financial documents. Public domain license permits unrestricted use. The dataset is small (135 pages) and limited to the FIN domain with no degradation, so its primary value is as a clean-class anchor for IQA heads and as the sole real-document Tibt contributor to SIG-G2-1 — it should not be relied upon as a standalone source but used in combination with tibhcr synthetic compositing.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 125 | Post-exclusion pages used for training |
| Val   | — | No formal val split defined |
| Test  | — | No formal test split defined |
| OOD   | — | Not designated as OOD benchmark |

**Ground Truth**: No ground truth labels are provided; annotation method is "None (Enrichment only)" at Tier 3 (Heuristic). All metadata is derived from Layer 2 enrichment (Docling OCR + layout extraction) rather than human annotation.

**L2 Metadata**: Available — 135 total samples. Key fields: domain (FIN: 100%), script_codes (Tibt: 96.3%, Latn: 3.0%, Zyyy: 0.7%), capture_methods (born_digital: 100%), content_flags (has_table: 71.1%, has_figure: 9.6%, has_signature: 0.7%).

### casia-hwdb2

Page-level Chinese handwriting corpus providing 4,076 training pages of controlled, high-quality HANS script from 1,019 writers; primary contributions are script_cls (HANS), handwriting_presence_cls (DOMINANT), handwriting_content_type_cls (PRINTED), presence_reg (1.0), and capture_method_cls (scanner). Academic Research Only license requires `license_restriction=academic` tagging on all derived samples; the test split (1,015 pages) is RESERVED for benchmark evaluation and must not be included in training manifests.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 4,076 | 3 sub-datasets combined (HWDB2.0/2.1/2.2) |
| Val   | — | No official val split defined |
| Test  | 1,015 | Writer-disjoint from train |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Human-annotated by NLPR staff; 1,019 writers each wrote 5 pages using Anoto digital pens, with per-line bounding boxes and GBK character labels derived from Anoto trajectory data. Provenance Tier 1 (original collection ground truth).

**L2 Metadata**: Not yet available.

### casia-hwdb2-line

Line-level Chinese handwriting corpus providing 33,400 training images of 100% handwritten Simplified Chinese (HANS); primary contributions are script_cls (cap use at ≤6,000 stratified samples to maintain class balance), handwriting_presence_cls (DOMINANT), handwriting_content_type_cls (PRINTED), presence_reg (1.0), and capture_method_cls (scanner). MIT license permits commercial use. Test split (10,440 images) is RESERVED for benchmark evaluation; MNV4 heads and resolution_quality_reg are excluded because the 128px fixed-height crops lack page-level orientation and reliable DPI context.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 33,400 | ~714 writers, writer-independent |
| Val   | 8,320 | ~178 writers, writer-independent |
| Test  | 10,440 | RESERVED — benchmark only |
| OOD   | — | No OOD split defined |

**Ground Truth**: Line-level Chinese transcriptions extracted from NLPR HWDB2 DGRL annotations by NLPR staff (Tier 1 ground truth); handwriting collected via Anoto digital pens, 100% coverage across all 52,160 line images.

**L2 Metadata**: Not yet available.

### cc-ocr

CC-OCR is a **primary contributor for CJK script detection (SIG-G2-1)** and a **secondary IQA contributor** via its 41% real-world subset. The MIT license removes all commercial-use barriers, making it the preferred CJK benchmark alternative to research-licensed M6Doc. The dataset's L2 metadata has domain_level1=UNK for all samples (Grade D audit), so it cannot be used for domain-stratified sampling until enrichment is complete; for script training, Hans=100% ground truth is reliable.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | No train split; benchmark-only |
| Val   | — | No val split; benchmark-only |
| Test  | — | No test split; benchmark-only |
| OOD   | 7,058 (6,533 available) | All splits — benchmark-only; 39 subsets across 4 tracks |

**Ground Truth**: Human expert annotation by benchmark annotators with professional review; 100% of 7,058 images carry multi-task OCR ground truth labels (text transcription in TSV `answer` field, covering scene text, multilingual OCR, document parsing, and key information extraction). Provenance Tier 1 (human-labeled).

**L2 Metadata**: Available — 6,284 total samples. Key fields: domain (UNK: 100% — unstratified), script_codes (Hans: 100%), capture_methods (unknown: 100%), content_flags (has_table: 15% / 942 samples).

### cocotext

COCO-Text plays a focused dual role in training: **CAMERA-class anchor** for `capture_method_cls` (SIG-G5-1) and **handwriting/legibility binary labeling source** for the G4 group (SIG-G4-1 and SIG-G4-2). These are the two heads where it contributes tier_1_annotation labels derived directly from the official annotation file.

For `capture_method_cls`, COCO-Text provides 43,686 training-eligible camera images — the largest single CAMERA-class source in the corpus. This is critical because the 100% real-image requirement for SIG-G5-1 (no synthetic) means camera diversity must come entirely from real-world datasets.

For G4, the word-level `class: machine_printed|handwritten` and `legibility: legible|illegible` annotations across 173K+ instances enable binary handwriting presence and legibility classification. The `presence_reg` and `legibility_reg` regression heads benefit from per-image aggregate ratios derived from these word-level labels.

**Important caveats**: COCO-Text is a scene text dataset, not a document dataset. It should not be used for document IQA training (blur_score, noise_score, contrast_score, overall_quality heads) because natural scene photographs have fundamentally different quality characteristics from scanned or camera-captured documents. The L2 audit confirms zero reliable quality labels.

**Benchmark protection**: Val and test splits (10,000 images each, 20,000 total) are RESERVED for the COCO-Text scene text benchmark. Only the 43,686-image train split is available for training — this is a hard constraint enforced by the dataset's benchmark status.

**License**: CC-BY-4.0 — commercial use permitted, attribution required. No synthetic cap constraints (0% synthetic). The 43,686 training images are freely usable without restrictions beyond attribution.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 43,686 | Annotated COCO 2014 train images |
| Val   | 10,000 | RESERVED — benchmark evaluation only |
| Test  | 10,000 | RESERVED — benchmark evaluation only |
| OOD   | — | Val/test serve as benchmark splits |

**Ground Truth**: Word-level bounding boxes and text transcriptions annotated by multiple human annotators (Cornell Vision Group); Tier 1 human-labeled provenance. Includes legibility (legible/illegible) and text class (machine printed/handwritten) attributes across 173K+ instances.

**L2 Metadata**: Available — 123,287 total samples. Key fields: domain (SCN: 100%), script_codes (Latn: 123,284, Cyrl: 1, Hang: 1, Hebr: 1), capture_methods (camera_smartphone: 100%), content_flags (has_handwriting: 5 samples flagged in L2; note: 86.7% of content_types classified as "handwritten" reflects LLM enrichment noise — actual dataset ground truth labels both classes).

### cvsi

CVSI-2015 is a primary contributor to SIG-G2-1 (script_cls) for Indic script differentiation, providing 8,616 samples across 8 Brahmic-family scripts (Deva, Beng, Gujr, Knda, Orya, Guru, Taml, Telu) with the most balanced per-class distribution (~1,000 per script) of any dataset in the pool; it is also the principal source of video-compression and motion-blur degradation examples for IQA heads. All 10 scripts are within the SIG-G2-1 19-class taxonomy. Research-only license from ICDAR 2015 competition.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 6,412 | Folder-per-script, 10 scripts |
| Val   | 1,069 | Folder-per-script, 10 scripts |
| Test  | 3,234 | Folder-per-script, 10 scripts |
| OOD   | — | No OOD split defined |

**Ground Truth**: Image-level script class labels derived from folder structure (no separate annotation files); annotated by human experts as part of the ICDAR 2015 competition; Tier 1 provenance (human-labeled).

**L2 Metadata**: Available — 10,715 total samples. Key fields: domain (SCN: 100%), script_codes (Deva 10.8%, Latn 10.6%, Orya/Gujr/Telu/Taml/Guru/Knda/Beng/Arab ~9-10% each), capture_methods (camera_smartphone: 100%), content_flags (empty — not populated).

### dibco

DIBCO is designated as a **benchmark-only** dataset for this project — the competition test sets (131 images) are permanently reserved for evaluation, and the project policy is to never train on any DIBCO split to preserve benchmark validity for measuring binarization and degradation-handling quality. The dataset's unique value lies in its gold-standard pixel-level binarization ground truth and extreme historical degradation cases (bleed-through, staining, fading) that serve as held-out stress tests for the IQA pipeline's contrast, noise, and artifact-handling capabilities. Any future relaxation of benchmark-only status would require explicit project approval, as contaminating this evaluation set would invalidate years of competition-comparable metrics.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 212 | Training split; in Layer 2 |
| Val   | — | No val split; competition design |
| Test  | 131 | RESERVED benchmark; excluded from L2 |
| OOD   | All splits — benchmark-only | |

**Ground Truth**: Pixel-perfect binary binarization masks (0=background, 255=foreground) annotated by human experts (competition organizers); Tier 1 provenance with 100% GT label coverage across all 343 images.

**L2 Metadata**: Available — 212 total samples. Key fields: domain (GOV: 100%), script_codes (Latn: 100%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 100%).

### diqa-5000

DIQA-5000 is the project's gold-standard IQA benchmark, holding 3-dimensional human MOS scores (overall, sharpness, color_fidelity) from 15 annotators per image alongside 8 classical IQA detector labels and 5,499 character-height-aware resolution quality scores. Despite this rich label density — which would nominally qualify it as ✅ Primary for IQA heads G1-1 through G1-6 and MNV4-H3 — the dataset carries a firm benchmark-only designation ("NEVER train on this dataset") to preserve the integrity of model evaluation. All 22 training heads therefore receive ❌ for DIQA-5000, and dataloaders must explicitly exclude it from training splits; its correct role is held-out calibration and SRCC/PLCC correlation testing against model predictions on the SIG-G1 and MNV4-H3 heads.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 3,850 | 350 ori + 3,500 res images |
| Val   | 550 | 50 ori + 500 res images |
| Test  | 1,100 | 100 ori + 1,000 res images |
| OOD   | — | Benchmark-only; no OOD split |

**Ground Truth**: 3-dimensional human Mean Opinion Scores (overall, sharpness, color_fidelity) on a 1–5 scale, crowdsourced from 15 annotators per image; Tier 1 provenance (human-labeled). MOS annotations cover only the 5,000 res/ enhanced images; the 500 ori/ base images lack MOS ground truth.

**L2 Metadata**: Available — 5,500 total samples. Key fields: domain (EDU 41.0%, SCI 30.6%, TEC 24.8%), script_codes (Hans 74.8%, Latn 22.9%, Hant 1.4%, Beng 1.0%), capture_methods (camera_smartphone 9.1%, synthetic 90.9%), content_flags (has_formula 63.5%, has_figure 53.2%, has_handwriting 20.8%, has_table 20.5%).

### doc3d

Doc3D's dominant contribution to the unified training corpus is the `warping_reg` head (SIG-G5-3), where its 102,064 synthetically rendered 3D-deformed documents with accompanying backward mapping and depth map annotations provide the richest geometric warp supervision of any available dataset. Because all samples are synthetic renders at fixed 448x448 resolution with no noise, blur, or real camera artifacts, the dataset contributes only minimally to IQA heads and cannot be used for capture method, resolution quality, or script classification training. The CC-BY-NC-SA license prohibits commercial use, and at ~209 GB the dataset is intentionally excluded from GCS; warping severity labels must be derived by extracting scalar statistics from the existing backward mapping NPY files, which have been downloaded but not yet extracted.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No official split; user-defined by mesh ID |
| Val   | Unknown | No official split; user-defined by mesh ID |
| Test  | Unknown | No official split; user-defined by mesh ID |
| OOD   | — | Not a benchmark dataset |

**Ground Truth**: Fully synthetic — 3D document renders generated via mesh deformation with seven exact ground truth types (3D coordinates, depth maps, UV maps, backward mapping, albedo, surface normals, checkerboard). Provenance Tier 0 (Exact); no human annotation required. Total dataset: 102,064 PNG images across 21 mesh ID subdirectories.

**L2 Metadata**: Not yet available.

### docalign12k

DocAlign12K is the largest available synthetic document warping dataset (30,338 images), contributing primarily to SIG-G5-3 (`warping_reg`) and SIG-G5-1 (`capture_method_cls=synthetic`). With parser implemented and base L2 metadata generated, it is the most integration-ready of the correction datasets, though 11 of 13 enrichment fields remain at 0% coverage (domain, language, script, layout, content flags). The unspecified license restricts commercial use pending author confirmation; the synthetic-only origin means this dataset cannot substitute for real camera or scanner capture distributions in heads requiring those classes.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 30,338 | Synthetically distorted images, 14 distortion groups |
| Val   | — | No validation split provided |
| Test  | 499 | Curated subset per test.txt |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Paired image structure — each distorted input is paired with a flat/rectified ground truth image at the matching path under `flat/`. Synthetic distortion applied by the dataset authors (South China University of Technology); provenance tier is Tier 0 (Exact), 100% GT label coverage.

**L2 Metadata**: Available — 30,338 total samples. Key fields: domain (GENERAL: 100%), script_codes (Zyyy: 100% — undetermined, needs LLM enrichment), capture_methods (synthetic: 100%), content_flags (empty — not yet populated).

### doclaynet

DocLayNet's primary role is as a **negative pool for IQA degradation heads** (providing high-quality, undegraded born-digital examples as upper-bound anchors) and a **primary contributor for SIG-G5-1 capture_method_cls** (81K clean born_digital labels). It is also a **strong secondary contributor for SIG-G2-1 script_cls** (Latin) and all SIG-G1 IQA heads as clean-document reference examples. License is CDLA-Permissive-1.0 (commercial use permitted). No OOD exclusions apply to this dataset — the single Arabic sample is negligible and does not trigger the Mongolian/Syriac/Georgian OOD rule.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 69,374 | COCO GT train.json membership |
| Val   | 6,489 | COCO GT val.json membership |
| Test  | 4,999 | COCO GT test.json membership |
| OOD   | — | 609 pages no COCO annotations (split=unknown) |

**Ground Truth**: Expert human annotation by IBM Research (DS4SD) using COCO-format bounding boxes and polygon segmentation across 11 layout classes; ~90% inter-annotator agreement reported; Tier 1 (human-labeled), with a double/triple-annotated subset for IAA measurement.

**L2 Metadata**: Available — 81,471 total samples. Key fields: domain (FIN 32.2%, TEC 29.4%, SCI 17.4%), script_codes (Latn 98.5%, Cyrl 0.6%, Jpan 0.4%), capture_methods (born_digital 100%), content_flags (has_figure 29.1%, has_table 26.0%, has_formula 8.1%).

### docreal

DocReal is a small (251-image) dewarping benchmark with MIT license whose primary training contribution is to the warping_reg and capture_method_cls heads, providing real paired camera-distorted and flatbed-scanned examples of perspective distortion and warping. At only 201 distorted images the dataset is too small to serve as a standalone training source and is best used as a held-out evaluation benchmark or combined with larger dewarping datasets such as AnyPhotoDoc6300 or Doc3D. The Layer 2 audit grade of C (label_accuracy 58.3%) and 100% unreliable composite category indicate enrichment gaps in domain, language, layout, and resolution fields that must be addressed before using metadata-derived labels for training.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | No official train split defined |
| Val   | — | No official val split defined |
| Test  | — | No official test split defined |
| OOD   | 251 | All images — user-defined splits; 201 distorted + 50 scanned GT |

**Ground Truth**: Paired-image GT — each of 50 flatbed-scanned documents is paired with ~4 camera-captured distorted variants via filename-based doc_id; provenance Tier 0 (Exact), 100% GT label coverage, no human annotators required.

**L2 Metadata**: Available — 200 total samples (audit subset of 201 distorted images). Key fields: domain (GENERAL: 100%), script_codes (Hani: 100%), capture_methods (camera_smartphone: 100%), content_flags (empty — not yet enriched).

### docsynth

DocSynth300K's primary role is layout pre-training — it supplies large-scale (300K) annotated layout examples for initializing DocLayout-YOLO before fine-tuning on real datasets such as DocLayNet. Being 100% synthetic, it is excluded from SIG-G5-1 (capture_method_cls), all IQA degradation heads where clean renders bias the score distribution, and all skew/warping heads. The Apache-2.0 license permits unrestricted commercial use; no synthetic mixing cap applies at the source level, but downstream task manifests should treat DocSynth300K images as born-digital synthetic and apply the ≤60% synthetic cap where required.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 300,000 | Single split; all images for pre-training |
| Val   | — | No val split provided |
| Test  | — | No test split provided |
| OOD   | — | Pre-training only; not used as benchmark |

**Ground Truth**: Programmatically generated synthetic annotations (Tier 0 — Exact). YOLO 8-coordinate polygon labels for 74 layout classes were created automatically by the Mesh-candidate BestFit document generation algorithm; no human annotation was performed.

**L2 Metadata**: Not yet available.

### document-haystack

Document Haystack is a **benchmark-only text-retrieval corpus** with no page image data, making it inapplicable to every visual training head in the pipeline. The CC-BY-NC-4.0 license prohibits training use, and the dataset's design as a long-context retrieval benchmark (400 documents, 8,250 queries) reserves it exclusively for RAG pipeline evaluation (Phase 10). No parser has been implemented yet, and no Layer 2 metadata exists for this dataset.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | Benchmark-only; no training split |
| Val   | — | Benchmark-only; no val split |
| Test  | 400 docs / 8,250 queries | All splits — benchmark-only |
| OOD   | — | N/A; benchmark-only dataset |

**Ground Truth**: Human expert annotations by Amazon Science researchers; query-document relevance judgments (binary or graded) covering all 8,250 queries against 400 documents. Provenance Tier 1 (Annotation). Note: this dataset contains no page images — it is a text-only long-context retrieval benchmark (PDFs and TXT files with extracted text).

**L2 Metadata**: Not yet available.

### drccbi

DRCCBI's primary contribution is as a real camera-captured dewarping benchmark providing both `capture_method=camera_smartphone` labels (SIG-G5-1) and real-world warping samples for SIG-G5-3 (`warping_reg`). As a paired warped/flat correction dataset with genuine camera perspective and page-curl artifacts, it complements synthetic warping sources (DocAlign12K, Doc3D) with camera-realistic warp distributions. The dataset is constrained by an unknown license (contact required before production use) and unknown total image count (repository verification required before assigning concrete sample estimates to training heads).

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | Warped/flat pairs; count unverified |
| Val   | — | No val split documented |
| Test  | Unknown | Warped/flat pairs; count unverified |
| OOD   | — | Not applicable |

**Ground Truth**: Paired image GT (Tier 0 Exact) — flat reference images captured or scanned separately from camera-warped inputs; 100% coverage via filename-matched warped/flat directory pairing, no human annotation required.

**L2 Metadata**: Not yet available.

### dzongkha-digits

Dzongkha-digits is a **supplementary Tibetan (Tibt) script source** with negligible volume (62 images locally, 1,000 full dataset) that contributes only to Tibt script diversity in SIG-G2-1 and G4 handwriting heads. CC-BY-4.0 license permits unrestricted commercial use with attribution. The dataset's primary constraint is size — only digit class 0 is downloaded locally; full 1,000-image download across all 10 digit classes is required before this dataset can provide meaningful training signal beyond what tibhcr already covers.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 1,000 (HF) / 62 (local) | All HF images in single train split; only class 0 downloaded locally |
| Val   | — | No official val split provided |
| Test  | — | No official test split provided |
| OOD   | — | Training-only dataset; no OOD split |

**Ground Truth**: Human expert annotation by 100 writers; image-level integer class labels (0-9) mapping to Tibetan digit Unicode (U+0F20-U+0F29); Tier 1 provenance (direct annotation, 100% GT label coverage).

**L2 Metadata**: Available — 62 total samples (local subset only). Key fields: domain (EDU: 100%), script_codes (Tibt: 100%), capture_methods (camera_smartphone: 100%), content_flags (has_handwriting: 62 samples populated).

### egyptian-handwriting

Egyptian Handwriting is the only commercially-viable Arabic cursive handwriting source in the corpus (CC-BY-4.0), providing 11,216 word-level images from 89 writers spanning ages 6–73. It serves as the primary Arab-script contributor to SIG-G2-1 (script_cls) and all five SIG-G4 handwriting heads (presence, legibility, content type, presence regression, legibility regression). Word-level crops limit its use for page-level IQA heads but the wide writer age range provides natural legibility variation.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 11,216 | Single parquet file; no official splits defined |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human expert annotation (89 writers, ages 6–73, Egyptian Arabic native speakers); Tier 1 provenance. Labels: Arabic word transcriptions in parquet `label` column with 100% coverage.

**L2 Metadata**: Not yet available.

### financebench

FinanceBench is a **benchmark-only evaluation corpus** — it MUST NOT contribute to any training pipeline under any circumstances. The CC-BY-NC-4.0 license prohibits commercial and training use, and training on this dataset would compromise benchmark integrity for RAG pipeline evaluation (Phase 10). All 54,120 images are stored under `02_benchmark_only/` and must remain exclusively in the OOD evaluation path.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | Benchmark reserved; training prohibited |
| Val   | — | Benchmark reserved; training prohibited |
| Test  | — | Benchmark reserved; training prohibited |
| OOD   | All splits — benchmark-only | 54,120 PNG images from 368 SEC filing PDFs |

**Ground Truth**: Human-annotated Q&A pairs (150 open-source of 10,231 total) with page-level evidence citations, produced by Patronus AI experts (Tier 1 provenance). No bounding boxes or layout annotations — Q&A benchmark only.

**L2 Metadata**: Available — 54,120 total samples. Key fields: domain (FIN: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (has_table: 100% populated).

### fintabnet

FinTabNet serves as a **pure born_digital negative pool** for IQA heads (blur/noise/skew all near zero) and as the primary large-scale contributor for the `born_digital` class of `capture_method_cls` (SIG-G5-1). Its research-only IBM license restricts commercial deployment but permits training use; the test split should be treated as OOD-reserved given its benchmark status in ICDAR 2019. The dataset's exclusive financial-table composition provides no diversity across domain, script, or degradation dimensions.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | Not broken out in source doc |
| Val   | Unknown | Not broken out in source doc |
| Test  | Unknown | Not broken out in source doc |
| OOD   | — | Test split OOD-reserved per ICDAR 2019 benchmark use |

**Ground Truth**: Automatic extraction via PDF-HTML document matching against SEC EDGAR filings (Tier 0 — Exact programmatic extraction). All 97,475 table images carry cell-level bounding boxes and cell text; no human annotation involved.

**L2 Metadata**: Available — 97,475 total samples. Key fields: domain (FIN: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (has_table: 100%).

### funsd

FUNSD contributes **authentic scanned-form IQA diversity** — its intentionally noisy real scans make it one of the few datasets providing genuine scanner degradation signals for blur, noise, and contrast heads. Despite its small size (149 training images), the 32% handwriting rate and 24% signature rate make it a critical source of handwriting presence labels (G4-1/G4-4). The test split (50 images) is BENCHMARK RESERVED and must be excluded from all training; the CC-BY-4.0 license permits commercial use with attribution.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 149 | Real noisy scanned forms |
| Val   | — | No val split defined |
| Test  | 50 | Benchmark reserved |
| OOD   | — | No OOD split |

**Ground Truth**: Human expert annotation of 199 scanned US administrative forms; entities labeled with 4 semantic types (question, answer, header, other) plus word-level bounding boxes and entity linking relations. Provenance Tier 1 (human-labeled), 100% coverage.

**L2 Metadata**: Available — 199 total samples. Key fields: domain (ADM 100%), script_codes (Latn 100%), capture_methods (scanner_adf 100%), content_flags (has_handwriting 32%, has_signature 24%, has_table 17%, has_figure 3%).

### funsd-plus

FUNSD+ is a **5.7× scale-up of FUNSD** providing the same scanner ADF and form-degradation signals with substantially more training volume (1,026 training images). Its primary constraint is audit defect D03 — `has_handwriting` is systematically false for all samples despite ~47% containing handwritten entries, making G4-x handwriting head labels unreliable until re-labeled; G4 contributions should be treated as 🟡 pending re-labeling. The CC-BY-4.0 license permits commercial use; the test split (113 images) is BENCHMARK RESERVED.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 1,026 | HuggingFace Arrow, pre-split |
| Val   | — | No validation split provided |
| Test  | 113 | Benchmark reserved |
| OOD   | — | No OOD split defined |

**Ground Truth**: Word-level BIO NER tags (9 classes: B/I-QUESTION, B/I-ANSWER, B/I-HEADER, B/I-OTHER, O) plus ground truth word transcriptions; extended from original FUNSD via mixed annotation (Tier 1); annotator details need verification. Known defect: has_handwriting=false for all samples despite ~47% containing handwritten entries.

**L2 Metadata**: Available — 1,139 total samples. Key fields: domain (ADM: 100%), script_codes (Latn: 100%), capture_methods (scanner_adf: 100%), content_flags (has_table: 37.8%, has_figure: 54.3%, has_formula: 1.8%).

### gnhk

GNHK (GoodNotes Handwriting Knowledge) provides 687 full-page handwritten document images with word-level polygon annotations and text transcriptions. All images are English handwriting captured on tablets, making it a small but high-quality calibration resource for SIG-G4-1 (handwriting_presence_cls) and SIG-G4-2 (handwriting_legibility_cls) via scribble-tagged illegible regions. CC-BY-4.0 permits commercial use.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 515 | JPG images with per-image JSON annotations |
| Val   | — | No val split defined |
| Test  | 172 | JPG images with per-image JSON annotations |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (ICDAR 2021); Tier 1 provenance. Word-level 4-point polygon annotations with text transcription, line index, and type flag. 100% coverage.

**L2 Metadata**: Not yet available.

### hasy

HASYv2 has a **narrow but unique role** in the multi-task pipeline: it is the **primary contributor for the MATHEMATICAL subclass** of `handwriting_content_type_cls` (SIG-G4-3), providing 151,410 training-eligible samples of handwritten math symbols across 369 LaTeX classes. No other dataset in the pool provides comparable coverage of mathematical handwriting at this scale.

Outside the MATHEMATICAL content-type head, HASYv2's utility is limited by its 32×32 pixel scale. The images are too small for orientation, skew, resolution quality, IQA, script detection, shadow/warping, or page-level analyses. The Zyyy (Common) script code explicitly excludes it from the 19-class `script_cls` head. Capture method is technically scanner_flatbed per L2 metadata but the actual input was crowdsourced pen-tablet drawing, creating a minor domain mismatch with document scanner classes.

**License constraint**: ODC ODbL v1.0 requires attribution (cite Martin Thoma, arXiv:1701.08380) and any published dataset derived from HASYv2 must remain open under the same license. Model weights trained on HASYv2 are not subject to the share-alike clause. **Benchmark protection**: the 16,823 test samples across all 10 folds are RESERVED and must not be used for training or validation. Use only the 151,410 training-split samples. The legacy `maths_handwriting/` subset (15K images) has lost its labels and should not be used; use `hasyv2_original/hasy-data/` exclusively.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 151,410 | 10-fold CV train splits combined |
| Val   | — | No dedicated val; folds serve as val |
| Test  | 16,823 | RESERVED — benchmark only, all folds |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Crowdsourced annotations via write-math.com (~100K contributors); each 32x32 symbol image labeled with numeric class ID (1-369) and LaTeX string by crowd contributors; Tier 1 (human-labeled) provenance with contributor-ID-based quality filtering.

**L2 Metadata**: Not yet available — aggregates JSON reports `total_samples: 0` with error "No Layer 2 metadata file found". Layer 2 enrichment pipeline has not yet been run against the full hasyv2 dataset.

### hiertext

HierText is the **primary gold-standard source for graded handwriting assessment** (G4-1 through G4-5), providing 1.2M word-level `handwritten` and `legible` binary annotations across 11,639 real camera images that enable derivation of continuous presence/legibility ratios. It also contributes as a strong primary for Latin script (G2-1) with 20+ language varieties, and as the sole 100%-real camera dataset eligible for capture_method_cls (G5-1). The CC-BY-SA-4.0 license requires ShareAlike on derivative works, which constrains how training labels derived from HierText can be redistributed. Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) scripts are absent from this dataset and remain OOD exclusions for G2-1.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 8,281 | Natural scene photos, Open Images source |
| Val   | 1,724 | Fully annotated with hierarchical text |
| Test  | 1,634 | Fully annotated with hierarchical text |
| OOD   | — | No OOD split; all splits training-eligible |

**Ground Truth**: Human expert annotations by the Google Research team, providing hierarchical polygon labels (paragraph → line → word) with binary `handwritten`, `legible`, and `vertical` flags at word and line granularity; Tier 1 provenance (human-labeled), 100% coverage across all 11,639 images with ~1.2M word annotations.

**L2 Metadata**: Available — 11,639 total samples. Key fields: domain (ADM 50.5%, TEC 17.8%, FIN 13.0%), script_codes (Latn 99.2%, Jpan 0.1%, Cyrl 0.1%, Hant 0.1%, Grek 0.1%, Deva 0.1%), capture_methods (camera_smartphone 100%), content_flags (has_handwriting 18.0% / 2,095 samples, has_table 2.1% / 241 samples).

### hindi-synth

This dataset is the **primary training source for the Devanagari (Deva) script class** in SIG-G2-1, contributing ~80K line-level images that cover diverse Devanagari font styles. It is licensed CC0 (public domain) with no usage restrictions. Being 100% synthetic, it is excluded from G5-1 `capture_method_cls` training and provides no IQA degradation signal, but it offers large-scale negative handwriting examples and high-quality anchor samples for IQA regression heads after a pseudo-labeling pass.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No split field; 99.99% unsplit |
| Val   | — | No val split defined |
| Test  | Unknown | TestSamples dir: 9 sample images only |
| OOD   | — | Not a benchmark dataset |

**Ground Truth**: Programmatic synthetic generation (Tier 0 — Exact). All 80,009 images paired with Devanagari text transcriptions via `data.csv` and per-image `.txt` files; labels are exact by construction with 100% coverage. No human annotation involved.

**L2 Metadata**: Not yet available.

### iam

IAM is the primary English cursive handwriting dataset for SIG-G4 heads. Its 657-writer diversity
provides the broadest natural spread of handwriting legibility and style available in a single
English-language corpus, making it the anchor dataset for `handwriting_legibility_cls`,
`handwriting_content_type_cls` (all CURSIVE), `presence_reg`, and `legibility_reg`. The lines.txt
`ok/err` segmentation flag is directly usable as a coarse legibility label, and the bounding box
hierarchy (form → line → word) enables handwriting area ratio derivation without additional
annotation. For SIG-G5-1 (`capture_method_cls`), IAM provides a clean SCANNER class contribution.
License is research-only (no commercial use), which is acceptable for model training but prohibits
redistribution of derived datasets commercially. The dataset is not benchmark-reserved, so the
full 130K image pool is available for training. As a Latin-only, grayscale, no-degradation-artifact
dataset, IAM is intentionally narrow on dimensions 1, 6, 12, and 13 and should be combined with
multilingual handwriting datasets (Muharaf, PUCIT-OHUL, TIBHCR) and degraded scan datasets for
full head coverage.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 6,161 | Text lines, 283 writers |
| Val   | 1,840 | Val1 (900) + Val2 (940) lines |
| Test  | 1,861 | Text lines, 128 writers |
| OOD   | — | Not benchmark-reserved; 3,491 lines unused in standard split |

**Ground Truth**: Human-expert annotations by the FKI Research Group at University of Bern; transcriptions and bounding boxes at form, line, word, and stroke-component levels for all 130,212 images. Provenance Tier 1 (human-labeled), with 100% label coverage and writer-independent splits enforced.

**L2 Metadata**: Not yet available.

### iiit-hw-hindi

IIIT-HW-Hindi is the primary Devanagari handwriting resource in the collection, providing 95,430 word-level crops from CVIT, IIIT Hyderabad, and is used principally as an OOD evaluation source for SIG-G2-1 `script_cls` (Deva class) and SIG-G4 handwriting heads (presence=DOMINANT, content_type=CURSIVE/MIXED). The research-only license prohibits commercial use, so all registry entries must carry `license_restriction=research`; training use requires explicit institutional clearance and should default to OOD evaluation only. With only 400 images extracted locally, the full 95K corpus is accessible via HuggingFace streaming (`load_dataset("c3rl/IIIT-INDIC-HW-WORDS-Hindi", streaming=True)`), and expanding the local extract to 5K–10K test images is recommended before running the IQA labeling pipeline.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 69,900 | Devanagari word crops, 100 extracted locally |
| Val   | 12,700 | 0 images extracted locally |
| Test  | 12,900 | 300 images extracted locally |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Word-level Devanagari Unicode transcriptions, annotated by CVIT (IIIT Hyderabad) using multiple Indic language experts with quality assurance review; Tier 1 (Human Expert Annotation) with 100% coverage across all 95,430 images.

**L2 Metadata**: Not yet available.

### im2latex

This dataset is the **primary source for the `code_cls` head** (G5-4) given that LaTeX formulas constitute markup/programming language content, and it provides reliable **born_digital** samples for G5-1. Licensed CC0 (public domain) with no usage restrictions. The 10,000-sample annotated subset is the working pool; the full 103,556-formula corpus could expand code_cls coverage. Being born-digital with no degradation, its IQA contribution is limited to providing "clean quality" anchors; augmentation would be required to generate blur/compression/noise signal from this source.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 83,883 | Rendered LaTeX PNGs from ArXiv |
| Val   | 9,319 | Standard validation split |
| Test  | 10,354 | Standard test split |
| OOD   | — | No OOD split defined |

**Ground Truth**: Annotations are synthetic — LaTeX source code extracted directly from ArXiv papers and rendered programmatically via a LaTeX pipeline. Provenance is Tier 0 (Exact); ground truth is 100% coverage by construction with no human annotation required.

**L2 Metadata**: Available — 10,000 total samples (annotated subset). Key fields: domain (EDU: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (has_formula: 100%).

### indicdlp

IndicDLP's primary training contribution is SIG-G2-1 (script_cls) — it is the largest source of real document images for 10 Indic script families (Devanagari, Bengali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Odia, Gurmukhi, Arabic), all of which are critically underrepresented in other layout and IQA datasets. It also contributes to SIG-G5-1 (capture_method_cls) as a real mixed-capture dataset. The MIT license permits unrestricted commercial use with no synthetic mixing constraints. The parser is not yet implemented (Layer 2 metadata pending), so script labels must be derived from the language metadata field in the COCO JSON; shadow and warping regression heads require additional labeling work before this dataset can contribute there.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~95,000 | COCO JSON, by_folder |
| Val   | ~12,000 | COCO JSON, by_folder |
| Test  | ~12,000 | COCO JSON, by_folder |
| OOD   | — | No OOD split defined |

**Ground Truth**: Human expert annotations (Tier 1) produced by AI4Bharat; COCO-format bounding boxes with 42 Indic-specific layout classes across 12 Indian languages; inter-annotator agreement details need verification.

**L2 Metadata**: Not yet available.

### invoices-kg

invoices-kg contributes 1,414 born-digital invoice images that serve as clean-reference anchors for capture_method_cls (born_digital class) and as strong negative examples for physical-degradation heads (blur, noise, shadow, warping). Its small size (1,414 images) limits standalone training utility, but it pairs well with SROIE and financebench for financial-document diversity. ODbL-1.0 license permits commercial use with attribution and ShareAlike compliance required.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 989 | 70%, random split seed=42 |
| Val   | 425 | 30%, random split seed=42 |
| Test  | — | No test split provided |
| OOD   | — | Not applicable |

**Ground Truth**: Mixed-method annotation (automated OCR + structured field extraction) from Kaggle-published invoice images; Tier 1 (Annotation) provenance. Annotator details not disclosed; labels cover invoice key-value fields, line items, and full OCR transcription (`ocred_text`) for all 1,414 images.

**L2 Metadata**: Available — 1,414 total samples. Key fields: domain (FIN: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (empty — not yet profiled).

### jssoda

JSSODa is the **primary contributor for Japanese script (Jpan) in G2-1 script_cls** and provides critical vertical-text orientation anchors for MNV4-H1 and SIG-G3-1, where the correct convention — vertical Japanese text labeled as 0° (upright) rather than 270° — is explicitly enforced by the parser. Its 100% synthetic nature makes it ineligible for G5-1 (capture_method_cls requires real images) and contributes only degenerate negatives to all IQA heads, so usage must be limited to script detection and orientation training tasks. The CC-BY-4.0 license permits unrestricted use without ShareAlike constraints.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 2,000 | All local images assigned to train |
| Val   | — | No val split defined |
| Test  | Unknown | Separate HuggingFace repo (llm-jp/JSSODa-test); not downloaded locally |
| OOD   | — | Not a benchmark dataset |

**Ground Truth**: Synthetic generation (programmatic rendering); orientation labels (is_vertical flag) and OCR text are exact by construction — Tier 0 provenance. Maintained by LLM-JP, CC-BY-4.0.

**L2 Metadata**: Available — 2,000 total samples. Key fields: domain (UNK 34.6%, ADM 31.1%, EDU 9.3%), script_codes (Jpan: 100%), capture_methods (synthetic: 100%), content_flags (has_formula: 0.1%).

### khatt

> **Status**: OOD evaluation source for Arabic cursive handwriting heads; not used for primary training.
>
> KHATT provides 1,633 paragraph-level handwritten Arabic images from 1,000 diverse writers,
> making it the most writer-diverse Arabic HW dataset in the collection. Academic Research Only
> license prevents use as primary training data — all contributions are OOD evaluation only.
> Mark all samples with `license_restriction=academic` in the OOD registry. Complementary to
> Muharaf (historical Arabic) for comprehensive ARAB handwriting OOD coverage.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~1,400 | Paragraph-level Arabic handwriting scans |
| Val   | ~233 | Paragraph-level Arabic handwriting scans |
| Test  | — | No test split provided |
| OOD   | ~1,633 | All splits used for OOD evaluation only |

**Ground Truth**: Paragraph-level Arabic Unicode transcriptions produced by 1,000 writers (self-transcribed samples), validated as ICFHR 2012 benchmark with 100% companion .txt coverage per image. Provenance Tier 1 (Human Expert Annotation).

**L2 Metadata**: Not yet available.

### kleister-charity

Kleister Charity contains 62,029 rendered page images (300 DPI PNG) from 2,776 British charity annual report PDFs, spanning train/dev/test splits. Reports contain mixed born-digital and scanned content with typed text, financial tables, and sparse handwritten annotations (signatures, margin notes). It is a primary contributor to SIG-G4-1 (handwriting_presence_cls) for mixed typed+handwritten content detection and provides strong layout diversity (tables, headers, figures). MIT license (code/labels); data under Open Government Licence.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 36,755 | From 1,727 PDFs |
| Val   | 10,639 | Dev-0 split; 440 documents |
| Test  | 14,635 | Test-A split; 609 documents |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (Applica.ai / ACL 2021); Tier 1 provenance. Document-level key-value labels (charity_name, charity_number, address, income, spending, report_date). 100% coverage.

**L2 Metadata**: Not yet available.

### kuzushiji

> **Status**: Primary training source for script_cls (JPAN handwritten) and handwriting heads; low-resolution negatives for resolution quality head.
>
> Pre-modern Japanese cursive character corpus providing 481K+ images across three sub-datasets.
> Use K-49 train split (232K) stratified to ~6,000 for script detection to avoid class imbalance.
> K-Kanji (140K, 3,832 classes) contributes rare Kanji diversity but requires class weighting.
> CC BY-SA 4.0 ShareAlike license: internal training is permitted; publishing derived datasets/models
> requires ShareAlike compliance. 28×28px images MUST be upscaled to ≥224px (INTER_CUBIC or
> INTER_LANCZOS4) before SigLIP2 inference — use as hard negatives for resolution quality head.
> K-MNIST test split (10,000) and K-49 test split (38,547) RESERVED for benchmark evaluation.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 292,365 | K-MNIST 60K + K-49 232,365 (combined) |
| Val   | — | No official val split in any sub-dataset |
| Test  | 48,547 | K-MNIST 10K + K-49 38,547 (benchmark-reserved) |
| OOD   | 140,424 | K-Kanji — no official train/test split |

**Ground Truth**: Image-level integer class labels derived from digitized historical Japanese books (NIJL collection), annotated by CODH expert annotators and mapped to Unicode codepoints via classmap CSVs. Provenance Tier 1 — extracted from manually annotated historical archives with 100% label coverage.

**L2 Metadata**: Not yet available.

### markushgrapher

MarkushGrapher is a highly specialized chemical structure dataset with very limited applicability to the core 22 training heads — its primary contribution is as a strong negative class for handwriting heads (G4-1, G4-4) and as high-quality IQA anchors (G1-1 through G1-3, G1-5, G1-6). The dataset is excluded from all script, orientation, skew, capture method, shadow, and warping heads due to its synthetic born-digital nature and domain specificity. The CC-BY-4.0 license permits unrestricted commercial use, but low training priority is confirmed (Phase 9, specialized element detection only); this dataset should not be included in general multi-task training manifests.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~188,000 | 80% split, chemical structure diagrams |
| Val   | ~23,500 | 10% split, same distribution |
| Test  | ~23,500 | 10% split, same distribution |
| OOD   | — | No OOD split defined |

**Ground Truth**: Synthetic generation — all ~235,000 images programmatically generated by DS4SD (IBM Research) with SMILES strings and atom/bond graph annotations. Provenance Tier 0 (Exact); deterministic pipeline, 100% coverage, no inter-annotator agreement needed.

**L2 Metadata**: Not yet available.

### mathverse

MathVerse is a **benchmark-only dataset** stored at `02_benchmark_only/mathverse/` and must not contribute to any training head. All 6,940 samples are reserved exclusively for evaluating geometric diagram IQA and mathematical visual reasoning quality. The dataset is MIT-licensed with no commercial restriction, but the project-level decision to reserve it as a held-out benchmark takes precedence — using it in training would contaminate evaluation results for fine-line quality and diagram clarity assessments.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | Benchmark-only; no training split |
| Val   | — | Benchmark-only; no val split |
| Test  | 3,940 | Testmini: 788 problems × 5 versions |
| OOD   | All splits — benchmark-only | Reserved for geometric diagram IQA evaluation |

**Ground Truth**: Mixed provenance (Tier 0/Tier 1) — math problems rendered programmatically with human-verified VQA annotations (question, answer, problem_type extracted from JSON/Parquet). 100% GT label coverage across 2,612 unique problems expanded to 15,000 samples via 6 textual/visual versions.

**L2 Metadata**: Available — 6,940 total samples. Key fields: domain (EDU: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (has_formula: 100%, has_figure: 100%).

### mdiw13

MDIW13 is the primary real-document dataset for SIG-G2-1 `script_cls`, providing 234,399 human-expert-labeled images across 9 ML-usable ISO 15924 script classes from flatbed-scanned printed documents and handwritten letters. The competition test set (55,814 images) is permanently RESERVED for benchmark evaluation and must never be used for training. Real/printed mixing caps do not apply to G2-1 since this dataset contributes exclusively to the real-scanned stratum; the 13th script class (Zyyy/undetermined, 21.7%) corresponds to competition_test samples and is excluded from training pools.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 203,538 | Main pool; 13 scripts, printed + handwritten |
| Val   | — | No dedicated val split in source |
| Test  | 30,861 | Competition Train split (labeled, usable) |
| OOD   | 55,814 | Competition Test — permanently RESERVED benchmark |

**Ground Truth**: Script classification labels assigned by human expert competition annotators via directory-based folder names (13 scripts) and a numeric ground truth file (0–12) for the competition test set; Tier 1 provenance (human-labeled), 100% coverage across all 290,213 images.

**L2 Metadata**: Available — 290,213 total samples. Key fields: domain (UNK: 100.0%), script_codes (Zyyy 21.7%, Beng 10.3%, Latn 10.2%, Arab 9.1%, Guru 9.1%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 52.6%, has_table: ~0%).

### mle2e

mle2e's primary training value is its 4-script multi-family coverage (Latn, Hans, Hang, Knda), with Korean/Hangul differentiation from Chinese/Han being the unique contribution absent from most other datasets. It also provides authentic camera_smartphone scene-text IQA variation (blur, noise, perspective distortion). At only 1,816 samples it is too small for standalone training; it should be combined with MLT19, CVSI, and SIW13 for the script_cls head. Research-only license restricts commercial deployment.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 1,174 | Pre-segmented text line crops, 4 scripts |
| Val   | — | No validation split provided |
| Test  | 642 | Pre-segmented crops; GT transcriptions available |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Script labels are human-annotated (Tier 1), encoded implicitly via directory structure (chinese/kannada/korean/latin folders). Text transcriptions are dataset-provided for the test set only; bounding box annotations exist in the original release but are absent from the local copy.

**L2 Metadata**: Available — 1,816 total samples. Key fields: domain (SCN 100%), script_codes (Latn 36.1%, Hans 25.3%, Hang 21.1%, Knda 17.4%), capture_methods (camera_smartphone 100%), content_flags (empty — scene text lacks document content flags).

### midv2020

MIDV-2020 provides the only **paired camera + flatbed scanner** captures in the training corpus, making it uniquely valuable for `capture_method_cls` head training: ~1K camera stills across 8 controlled conditions (projective distortion, low lighting, highlight, backgrounds) paired with ~3K high-quality flatbed scans of the same 10 document types. It is also the **sole Greek script (Grek) source** in the corpus (400 samples from `grc_passport`) and supplements Cyrillic coverage from MIDV-500. Orientation labels are derived from the `scan_rotated` archive (rotation class from archive name). CC BY-SA 2.5 requires attribution to Arlazarov et al. and Generated Photos for face images, and ShareAlike on derivatives.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No formal train split defined |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | 4,000 images across capture-mode archives (photo, scan_upright, scan_rotated, templates) |

**Ground Truth**: Human expert annotation (Tier 1) in VIA v2 JSON format; per-image polygon quads for document boundary and individual fields, with native-script field text values (names, dates, document numbers, MRZ). ~100% coverage across all 4,000 images and 10 document types.

**L2 Metadata**: Not yet available as aggregates JSON. L2 metadata file `midv2020_metadata.json` was created (4,000 samples, enrichment v2) but `midv2020_stats.json` aggregate has not been generated.

### midv500

MIDV-500 is the **primary Cyrillic script source** in the training corpus, contributing ~430 real camera-captured images from six Cyrillic-script countries (Russia, Ukraine, Belarus, Bulgaria, Serbia, Kazakhstan) out of 50 total countries. Additional value as IQA training data (blur/noise/contrast/compression from mobile video frames) and camera_smartphone capture method training (~3,612 stills). Frame selection from 15,050 raw video frames down to 3,612 usable JPGs requires pre-processing; the MIT license permits unrestricted commercial use. No explicit orientation or skew GT — derived labels only.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No official split defined in source |
| Val   | — | No val split defined |
| Test  | Unknown | No official split defined in source |
| OOD   | — | 15,050 video-frame annotations; 3,612 usable JPG stills |

**Ground Truth**: Tier 1 human-expert annotation; field-level quad coordinates and text values per identity document type (50 country templates), covering names, dates, document numbers, and nationalities across 50 countries.

**L2 Metadata**: Available — 15,050 total samples. Key fields: domain (GOV: 100%), script_codes (Latn 76%, Cyrl 10%, Hans 6%, Arab 4%, Grek/Jpan 2% each), capture_methods (camera_smartphone: 100%), content_flags (has_figure: 100%).

### mlt19

MLT19 is a primary contributor to SIG-G2-1 `script_cls` for the camera-captured scene text distribution, providing 10,000 human-GT-labeled train images (96.6% language accuracy) and 9,657 VLM-labeled test images (67% accuracy; test split should be downweighted or excluded for high-precision script heads). It is the sole 100%-camera dataset for SIG-G5-1 `capture_method_cls`, contributing all 19,657 images to the camera/smartphone stratum. The Latin language conflation (KI-009: all European Latin-script languages mapped to "en" for train split, partially resolved via LLM refinement in v5) means Latin-script subclass precision is reduced; this does not affect the script-family level classification but limits language-level training signal.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 10,000 | Public GT; word polygons + language labels |
| Val   | — | No val split exists |
| Test  | 9,657 | No public GT; VLM-derived labels (~67% accuracy) |
| OOD   | — | Not designated OOD |

**Ground Truth**: Word-level quadrilateral polygons with 10-class language labels, annotated by ICDAR 2019 competition human experts (Tier 1 — human-labeled); train split only, 96.6% language accuracy; test GT never publicly released (competition standard practice).

**L2 Metadata**: Available — 19,657 total samples. Key fields: domain (SCN 100%), script_codes (Latn 54.5%, Deva 10.4%, Zyyy 8.5%, Hang 6.0%, Arab 5.2%), capture_methods (camera_smartphone 100%), content_flags (has_table: 12 samples, has_handwriting: 3 samples).

### muharaf

Muharaf is the primary Arabic cursive handwriting contributor to all G4 handwriting heads, providing
24,952 expert-annotated images with PAGE XML production metadata confirming cursive type and explicit
quality variation from clean to illegible. The CC BY-NC-SA 4.0 license permits non-commercial
research training, but commercial deployment is restricted; all OOD registry entries should be
flagged `license_restriction=cc-by-nc-sa`. The 50.3% UNK domain share (aggregate stats) should be
resolved via enrichment before using domain-stratified splits.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No official splits; all public images unsplit |
| Val   | — | No official val split provided |
| Test  | — | No official test split provided |
| OOD   | — | Not a benchmark-only dataset; custom splits recommended |

**Ground Truth**: Expert human annotations via PAGE XML (W3C standard); 24,495 line-level transcriptions authored by Arabic manuscript specialists at Phoenix Center for Lebanese Studies (USEK), Tier 1 provenance. QA metadata embedded in PAGE XML (Creator + transcription_QA fields).

**L2 Metadata**: Available — 25,711 total samples. Key fields: domain (top 3: UNK 50.3%, ADM 26.9%, PER 12.4%), script_codes (Arab: 100%), capture_methods (scanner: 100%), content_flags (has_handwriting: 100%, has_signature: 100%).

### nara-1950-census

NARA 1950 Census is a **primary contributor for handwriting presence detection (SIG-G4-1)** and **mixed typed+handwritten content type classification (SIG-G4-3)**, providing 695 scanned census enumeration schedules where 100% of data content is handwritten on pre-printed tabular government forms. It is also a **primary contributor for scanner capture method (SIG-G5-1)** and **Administrative/Government domain classification**. The dataset fills gap SIG-G4-3 (mixed typed+HW) and SIG-G4-1 (handwriting in structured documents). Public Domain license permits unrestricted commercial use with no attribution required. Current sample is 695 images from Alabama; target is ~25K stratified across all states.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 695 | Current partial Alabama sample |
| Val   | — | No val split defined yet |
| Test  | — | No test split defined yet |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Filename-derived metadata (census_id, state, serial, page) extracted by parser; no human annotation of content labels. Handwriting presence is 100% by dataset nature (all pages are handwritten census forms). Provenance Tier 3 (Heuristic — dataset-level labels from known content).

**L2 Metadata**: Not yet available.

### multimodal-textbook

Multimodal Textbook serves as a **primary born-digital contributor** for capture method classification and Latin script coverage, and as a uniquely strong source of formula- and figure-rich STEM content for IQA and overall quality heads. Its Apache-2.0 license imposes no usage restrictions, and its fully born-digital origin means it correctly maps to the `born_digital` capture class with no synthetic mixing concerns (real-only for SIG-G5-1 is fully satisfied). The dataset's video-frame origin limits its utility for scan-related degradation heads (shadow, warping, skew) and restricts script diversity to Latin/English only, making it a complement rather than a replacement for document-origin datasets in multi-script or physical-degradation heads.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No split structure in local sample |
| Val   | — | Not defined in local sample |
| Test  | — | Not defined in local sample |
| OOD   | — | Not a benchmark dataset |

**Ground Truth**: Annotations extracted automatically via PDF/Parquet extraction from 67,434 educational YouTube videos; Tier 0 (Exact) provenance with 100% GT label coverage — no human annotation required.

**L2 Metadata**: Available — 1,113 total samples. Key fields: domain (EDU: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (has_formula: 100%, has_figure: 100%).

### multilingual-scripts

Multilingual-scripts is the **primary multi-script diversity contributor for SIG-G2-1 script_cls**, being the only single-collection source covering 4 distinct script families (CJK, Indic, RTL, Tibetan) with ground-truth ISO 15924 labels. Its value is script breadth, not volume — at 3,279 total images it is supplementary relative to dedicated per-script datasets. The main constraints are: (1) capture_method=unknown for all samples prevents SIG-G5-1 capture classification training; (2) JSSODa (61% of the collection) is synthetic, which may limit naturalness for IQA heads; (3) domain_level1=UNK for all samples prevents domain-stratified sampling.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No explicit split defined in source doc |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as benchmark-only |

> **Subdataset breakdown (all 3,279 images, no formal splits)**:
> jssoda=2,000 (Jpan/synthetic), nepal_devanagari=717 (Deva/real), arabic_ocr=500 (Arab/scanned), dzongkha_digits=62 (Tibt/synthetic)

**Ground Truth**: ISO 15924 script-class labels (Jpan, Deva, Arab, Tibt) assigned per subdataset; provenance is ground truth — labels derive directly from dataset collection identity, not annotation campaigns. All 3,279 samples are confirmed printed (content_type=printed) with no handwriting present.

**L2 Metadata**: Available — 3,279 total samples. Key fields: domain (UNK: 100%), script_codes (Jpan 61%, Deva 22%, Arab 15%, Tibt 2%), capture_methods (unknown: 100%), content_flags (empty — none populated).

### ndl-docl

NDL-DocL provides 2,290 historical Japanese document images from the National Diet Library, split into rare books (1,219 images, pre-1868) and modern publications (1,071 images, post-1868). The rare books subset contains kuzushiji (historical Japanese cursive) handwriting regions annotated in Pascal VOC XML, making it a primary contributor to SIG-G4-1 (handwriting_presence) for Japanese script and filling the HISTORICAL document age dimension. Public Domain Mark (PDM 1.0) imposes zero restrictions.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~2,290 | No official splits; all images in single collection |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (NDL Lab annotators); Tier 1 provenance. Pascal VOC XML bounding boxes with layout classes (kuzushiji, typography, illustration, seals/stamps for rare books; headline, caption, text lines, tables for modern). 100% coverage.

**L2 Metadata**: Audited 2026-02-25 (5 samples only — stub). Key findings: capture_method=scanner_flatbed, has_handwriting=true (kotenseki subset), domain_level1=UNK (recommend HIS/LIT).

### ndl-minhon

NDL-Minhon is the largest kuzushiji dataset in the corpus (32,822 images, 523,283 line annotations) and serves as the dominant contributor for SIG-G4-1 (handwriting_presence) where virtually all images contain handwritten content. It uniquely fills the handwriting_content_type=specialized class (kuzushiji historical cursive) and provides the deepest HISTORICAL document age coverage. The crowdsourced annotations include isVertical flags enabling orientation training. **License caution**: CC-BY-SA 4.0 copyleft requires derivative works to maintain the same license.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~32,822 | v1 (4,688) + v2 (28,134); no official splits |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Crowdsourced (Minna de Honkoku platform volunteers); Tier 2 provenance. Line-level bounding boxes + text transcriptions + isVertical flag. 523,283 annotations. 100% coverage.

**L2 Metadata**: Audited 2026-02-25 (500 samples). Key findings: capture_method=scanner_flatbed, has_handwriting=true (100%), iso15924_script=Hani (kuzushiji manuscripts), domain_level1=UNK (recommend HIS).

### nepali-handwritten

nepali-handwritten is the sole real-camera handwriting contributor for the Devanagari (Deva) script class in SIG-G2-1, providing 958 word-level images with GT script labels and confirmed camera_smartphone capture for SIG-G5-1. At only 958 images it is a supporting contributor rather than a primary training source; it fills a unique niche as real handwritten Devanagari distinct from synthetic printed data (hindi_ocr_synthetic) and must be combined with larger Indic datasets to approach the 60K handwriting pool target. The CC-BY-4.0 license permits commercial use with attribution (pending final verification per Section 9.5).

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~766 | 80% split, by_folder |
| Val   | — | No validation split provided |
| Test  | ~192 | 20% split, by_folder |
| OOD   | — | Not a benchmark dataset |

**Ground Truth**: Human-expert annotated PASCAL VOC bounding boxes (word/character level, exact granularity unconfirmed) with no text transcriptions; Tier 1 annotation provenance collected by Sweekar Dahal via Kaggle (2023).

**L2 Metadata**: Available — 958 total samples. Key fields: domain (EDU: 100%), script_codes (Deva: 100%), capture_methods (camera_smartphone: 100%), content_flags (has_handwriting: 100%, has_figure: 0.1%, has_table: 0.1%).

### nist-sd19

NIST SD-19 is a **primary contributor for handwriting heads (SIG-G4)** and a **strong Latin script anchor (SIG-G2-1)**. Its 3,669 full-page HSF scanned forms with 100% handwriting presence make it an ideal DOMINANT-class anchor for `handwriting_presence_cls` and `presence_reg`. The 3,600 writer pool provides natural legibility variation suitable for `handwriting_legibility_cls` and `legibility_reg` with model-derived or human annotation scoring. For `handwriting_content_type_cls`, the isolated-character and block-letter content maps cleanly to the PRINTED class. The dataset is public domain with no license restrictions and no benchmark-reserved splits.

The 810K+ character images (via by_class/by_field archives) are character-scope rather than page-scope and may supplement character-level handwriting tasks, but the primary training value for the multi-task pipeline lies in the 3,669 page-level HSF images. The binary 1-bit format limits IQA head utility (contrast, compression heads not applicable), and the fixed 300 DPI / flatbed capture means this dataset does not contribute diversity across resolution range, shadow, or warping dimensions. Orientation and skew labels must be synthetically derived via rotation augmentation and classical estimation respectively.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No formal split defined in source |
| Val   | — | No val split documented |
| Test  | Unknown | No formal split defined in source |
| OOD   | — | Not benchmark-only; no OOD split |

**Ground Truth**: Human expert annotation by NIST following standard collection protocol. Provenance Tier 1 (Annotation) — character-level labels derived from filename/directory structure across 3,600 writers; 100% GT coverage on 3,669 HSF full-page scanned forms.

**L2 Metadata**: Available — 3,669 total samples. Key fields: domain (GOV: 100%), script_codes (Latn: 100%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 100%).

### nist-sd2

NIST-SD2 is a narrow-domain supplementary dataset whose primary value is providing clean
negative examples for IQA degradation heads (all ➖) and binary B&W form images for the
binarization-status diversity dimension. Its synthesized handprint contributes to SIG-G4 heads
at secondary weight only, because the uniform legibility distribution (machine-generated fills)
understates natural handwriting variability and would distort legibility regression if used as a
primary source. The most critical constraint is the L2 metadata capture_method error: all 5,590
samples are labeled `scanner_flatbed` but the dataset is programmatically generated — this must
be corrected to `SYNTHETIC` before use in SIG-G5-1 (`capture_method_cls`) training to avoid
mislabeling the SCANNER class. The dataset is public domain (no license restrictions) and not
benchmark-reserved, so the full 5,590-page pool is available. Given the 1988 vintage form
layouts and synthesized nature, NIST-SD2 should be treated as a diversity supplement rather than
a primary training source for any head, and should be balanced against real scanned form datasets
(FUNSD, SROIE) for form-domain coverage.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 4,472 | 80%, locally created split (seed 42) |
| Val   | 559 | 10%, locally created split (seed 42) |
| Test  | 559 | 10%, locally created split (seed 42) |
| OOD   | — | No OOD split; not benchmark-reserved |

**Ground Truth**: Synthesized (computer-generated) IRS 1040 Package X tax forms with exact field-value annotations in custom .fmt files; Provenance Tier 0 (Exact) — 100% GT coverage, no human annotation required.

**L2 Metadata**: Available — 5,590 total samples. Key fields: domain (GOV: 100%), script_codes (Latn: 100%), capture_methods (scanner_flatbed: 100% — NOTE: label is incorrect; dataset is synthetic, not scanned), content_flags (has_handwriting: 100%, has_formula: 3.6%, has_figure: 0.4%).

### nist-sd6

NIST SD-6 is a **secondary handwriting contributor** that complements NIST SD-19 by providing mixed printed-form / handprint pages rather than pure handwriting. Its primary value for the multi-task pipeline is: (1) reinforcing the SCANNER capture class for `capture_method_cls`; (2) adding MIXED content-type examples for `handwriting_content_type_cls` (printed form skeleton + printed handprint entries); and (3) providing MODERATE/SUBSTANTIAL handwriting presence examples for `handwriting_presence_cls` where the handwriting fills only the form fields, not the full page.

The dataset is public domain with no license restrictions and no benchmark-reserved splits. It is NOT a benchmark dataset and the full 5,595 images are available for training. Key limitations: the synthesized nature (900 simulated respondents rather than real census submissions) reduces diversity compared to real-world form datasets; the 1-bit binary format limits IQA head contributions; and the 1988 form design may not generalize to modern form layouts. The `capture_method` of `scanner_flatbed` is technically correct for the synthesis process (flatbed-scanned output) and should be retained in training. Orientation and skew labels require synthetic augmentation and classical estimation respectively, as no native geometric labels are provided.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | No official splits; full set used for training |
| Val   | — | No official splits provided |
| Test  | — | No official splits provided |
| OOD   | — | Not a benchmark dataset; all 5,595 images training-eligible |

**Ground Truth**: Field-level text transcriptions in custom .fmt files, annotated by NIST via synthesized census form construction with real handprint overlays (Tier 0/Tier 1 provenance). Annotation method is Mixed; 100% field coverage with no bounding boxes provided.

**L2 Metadata**: Available — 5,595 total samples. Key fields: domain (GOV: 100%), script_codes (Latn: 99.9%, Hant: 0.1%, Beng: 0.0%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 100%, has_formula: 3.6%, has_figure: 0.1%).

### ocr-quality

OCR-Quality's primary contribution is the SIG-G1-6 overall_quality head, providing 1,000 human-annotated quality scores that serve as an independent cross-validation source for DeQA-Doc predictions — the SRCC target is >0.80 against this dataset. The dataset is CC0 (public domain) with unrestricted commercial use, making it one of the most license-friendly in the corpus. Key constraints are its small size (1,000 images), the inverted 1-best/4-worst scoring scale that requires normalization before any training use, and the unknown capture method that limits its utility for SIG-G5-1; it should be treated as a validation and calibration dataset rather than a primary training source for any head other than overall_quality.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 1,000 | Single Parquet file, all images |
| Val   | — | No official val split |
| Test  | — | No official test split |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Human crowd-annotated quality scores on a 1–4 inverted scale (1=best, 4=worst), assigned via crowdsourced annotation (Zhang et al., 2025); provenance Tier 1 (Annotation). OCR text transcriptions are dataset-provided (Qwen2.5-VL-72B), not traditional OCR engines.

**L2 Metadata**: Available — 1,000 total samples. Key fields: domain (SCI 28.8%, EDU 17.6%, TEC 16.7%), script_codes (Hans 54.7%, Latn 40.0%, Hant 4.0%), capture_methods (unknown 100%), content_flags (empty — not yet populated).

### ohr-bench

OHR-Bench is explicitly designated as a benchmark-only dataset (`training_suitable=false`) and contributes zero samples to any of the 22 training heads. Its value is confined to evaluation: measuring how OCR quality errors propagate through RAG pipelines using controlled semantic and formatting noise variants across 8,498 Q&A pairs. The dataset's born-digital origin means it provides high-quality baseline pages free of scan artifacts, skew, blur, or compression noise, making it an ideal clean reference for evaluating IQA detector false-positive rates — but this evaluation role is distinct from training. Any attempt to use OHR-Bench samples for training should be explicitly blocked at the dataloader level.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | No official train split exists |
| Val   | — | No official val split exists |
| Test  | — | No official test split exists |
| OOD   | 8,561 | All splits — benchmark-only, single unsplit pool |

**Ground Truth**: Automatic programmatic extraction from born-digital PDFs (Tier 0 — Exact); gt_text column in HuggingFace Parquet covers 100% of pages with structured ground truth, no human annotation required.

**L2 Metadata**: Available — 8,303 total samples. Key fields: domain (GOV 30.4%, FIN 25.7%, TEC 20.8%), script_codes (Latn 94.4%, Zyyy 3.7%, Hans 1.3%), capture_methods (born_digital 100%), content_flags (has_figure 31.0%, has_table 25.2%, has_formula 1.3%).

### omnidocbench

OmniDocBench is a **benchmark-only evaluation corpus** (path: `02_benchmark_only/omnidocbench/`) reserved for Phase 10 pipeline evaluation; it must not enter training manifests unless the stratified internal split is explicitly activated. Its primary training utility is as a source of **clean born-digital reference pages** that anchor the high-quality end of IQA head distributions, and as a **layout-rich corpus** with 19 layout categories and strong content-type diversity (figures, tables, formulas). The research-only license and the single-capture-method limitation (100% born_digital, 300 DPI, no degradation) mean it cannot contribute to any head requiring scan artifacts, camera distortion, skew, shadow, or warping examples.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 938 | Internal dev split only (stratified 70%) |
| Val   | 203 | Internal dev split only (stratified 15%) |
| Test  | 217 | Internal dev split only (stratified 15%) |
| OOD   | All 1,355 pages — benchmark-only (formal eval uses full corpus) | |

**Ground Truth**: Human expert annotations across 20,000+ block-level and 80,000+ span-level elements; provenance Tier 1 (Annotation), sourced from official structured PDF extraction by the OmniDocBench authors (Chen et al., CVPR 2025).

**L2 Metadata**: Available — 377 total samples. Key fields: domain (UNK: 100% — domain_level1 unpopulated, grade-cap defect ODB-D01), script_codes (Latn: 94.7%, Hans: 5.3%), capture_methods (born_digital: 100%), content_flags (has_formula: 23.3%, has_figure: 15.1%, has_table: 6.1%).

### openlid-v2

OpenLID-v2 is a **text-only corpus** (116M+ samples, 201 language-script pairs, 27 ISO 15924 scripts) with no image component and no direct contribution to any of the 22 training heads. Its critical role in the pipeline is as an indispensable upstream text source for `synth-multiscript-v3`: its ISO 15924 codes drive script-aware font selection and rendering, producing the 190K+ synthetic images that directly contribute to SIG-G2-1 (`script_cls`) training. MIT license permits unrestricted commercial use. No traditional parser or download is required — accessed via HuggingFace streaming API through `TextCorpusManager` with three-tier local/GCS/streaming caching.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | Text-only corpus — no train/val/test splits; 116M+ samples streamed dynamically |
| Val   | — | No split; synthetic generator applies splits to generated images, not source text |
| Test  | — | No split |
| OOD   | — | Text corpus only — no images; not applicable as benchmark dataset |

**Ground Truth**: Language codes (ISO 639-3 + ISO 15924 format, e.g., `eng_Latn`) are automatically extracted from web-sourced text by the OpenLID team using fastText-based language identification filtering; provenance tier is Tier 1 (Automatic Extraction) with 100% label coverage across 201 language-script pairs.

**L2 Metadata**: Not yet available.

### openpecha-ocr-drutsa

OpenPecha OCR Drutsa provides 32,364 line-level images of Tibetan script text from woodblock prints, manuscript pages, and modern Tibetan typography. It is the primary Tibetan (Tibt) script contributor to SIG-G2-1 (script_cls), filling a unique abugida writing system gap. The dataset contains a mix of handwritten manuscripts and printed woodblock material, giving partial signal for SIG-G4-1 (handwriting_presence). Line-level crops limit page-level IQA contributions. CC-BY-4.0 permits commercial use.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 32,364 | Single training split; no explicit train/test/val |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as OOD |

**Ground Truth**: OCR ground truth text (Unicode Tibetan transcriptions); Tier 1 provenance. Each record has unique ID, binary image, and Tibetan text label. 100% coverage.

**L2 Metadata**: Not yet available (Layer 1 metadata generated).

### pdmocr-part1

PDM-OCR Part 1 provides ~2,713 images of historical Japanese documents spanning 1870s–1940s with character-level bounding box annotations (JSON + Pascal VOC XML). Its preservation of archaic kanji forms without normalization makes it uniquely valuable for SIG-G2-1 (script_cls) where the model must handle historical Japanese variants. The decade-organized structure enables stratified sampling for document age diversity. All content is printed typography (no handwriting). Public Domain Mark (PDM 1.0) imposes zero restrictions.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~2,713 | Organized by decade (1870–1940s) and category |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (NDL Lab + LINE Corporation annotators); Tier 1 provenance. Character-level bounding boxes + text transcriptions in dual formats (JSON + Pascal VOC XML). 100% coverage.

**L2 Metadata**: Audited 2026-02-25 (63 samples). Key findings: capture_method=scanner_flatbed, has_handwriting=false (100% historical printed typography), domain_level1=UNK (enrichment opportunity via NDC classification).

### pdmocr-part2

PDM-OCR Part 2 is the only dataset in the corpus with explicit text direction ground truth (vertical/horizontal/RTL) at the line and block level via the NDLOCR XML DIRECTION attribute, making it uniquely valuable for SIG-G3-1 (orientation_cls) validation on Japanese text. At ~3,997 images spanning 1870s–1960s (extending 20 years beyond Part 1) with a 3-level annotation hierarchy (PAGE/LINE/CHAR), it serves as the primary Japanese historical text resource for orientation and script detection. All content is printed typography. Public Domain Mark (PDM 1.0) imposes zero restrictions.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~3,997 | Organized by decade (1870s–1960s); NDLOCR XML |
| Val   | — | No val split defined |
| Test  | — | No test split defined |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (NDL Lab + Morpho AI Solutions annotators); Tier 1 provenance. NDLOCR XML with 3-level hierarchy (PAGE/LINE/CHAR) plus explicit DIRECTION attribute (vertical/horizontal/RTL). 100% coverage.

**L2 Metadata**: Audited 2026-02-25 (50 samples). Key findings: capture_method=scanner_flatbed, has_handwriting=false (historical typography). Enrichment opportunity: DIRECTION attribute not yet extracted into L2 metadata.

### popp-line

POPP-line provides 4,794 line-level handwritten text images from French census records (19th–20th century), each with a French text transcription. It is a primary contributor to SIG-G4-1 (handwriting_presence_cls) for 100% handwritten content and provides unique French-language handwriting diversity in a government/administrative domain. Line-level crops limit page-level IQA signal. CC-BY-4.0 permits commercial use.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 3,835 | Line-level crops from census forms |
| Val   | 480 | Line-level crops from census forms |
| Test  | 479 | Line-level crops from census forms |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (POPP project / Constum et al., 2022); Tier 1 provenance. French text transcriptions of handwritten census lines. 100% coverage.

**L2 Metadata**: Not yet available (Layer 1 metadata generated).

### pubtabnet

PubTabNet's primary training value is as a **large-scale BORN_DIGITAL negative pool** for SIG-G5-1 capture_method_cls (~519K labels) and as a **large handwriting-absence pool** for SIG-G4-1/G4-4. Its contribution to IQA heads (G1 group) and resolution quality (MNV4-H3, SIG-G5-5) is limited by the small table-crop image size and single-domain scientific bias. License is CDLA-Sharing-1.0 (share-alike commercial use permitted). No OOD script exclusions apply — the trace non-Latin samples (<0.04%) are negligible.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 500,777 | PDF-extracted scientific tables |
| Val   | 9,115 | Same source, held-out |
| Test  | 9,138 | No extracted layout/OCR annotations |
| OOD   | — | No OOD split defined |

**Ground Truth**: Automatically extracted via PDF/XML alignment from PubMed Central Open Access PDFs; Tier 0 (exact programmatic extraction) with 100% cell-level HTML structure and bounding box coverage across all 519K images.

**L2 Metadata**: Available — 519,030 total samples. Key fields: domain (SCI: 100%), script_codes (Latn: 100%, trace Hant/Hans/Deva), capture_methods (born_digital: 100%), content_flags (has_table: 100% populated).

### pucit-ohul

pucit-ohul is the primary real-data anchor for the Arabic script family (Urdu Nastaliq variant) in the handwriting pool, contributing 7,401 line-level GT-labeled samples to SIG-G2-1 (script_cls: Arab) and SIG-G4 (handwriting heads: DOMINANT presence, CURSIVE content type). The dataset is licensed CC0 / non-commercial research only, which restricts commercial deployment of any model trained with it. At 7,401 images it is a moderate-sized handwriting contributor but does not reach the 60K pool target on its own, requiring combination with muharaf and other Arabic-script datasets.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 6,489 | train_lines/ folder, XLSX GT |
| Val   | — | No validation split provided |
| Test  | 912 | test_lines/ folder, XLSX GT |
| OOD   | — | Not a benchmark dataset |

**Ground Truth**: Human expert annotation; line-level Urdu transcriptions stored in Excel (.xlsx) with original ("Caption") and revised ("Revised") columns; Tier 1 (Annotation) provenance, 100% GT coverage.

**L2 Metadata**: Available — 7,401 total samples. Key fields: domain (EDU: 100%), script_codes (Arab: 100%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 7,401).

### q-doc

Q-Doc is a pure IQA benchmark dataset whose primary contribution is image-level overall quality scores for camera-captured document images, making it a targeted source for the SIG-G1-6 overall_quality and SIG-G5-5 resolution_quality_reg heads. The dataset is small (~4,260 images), secondary qualities such as blur and noise are inferrable but not explicitly labelled per degradation dimension, and the unknown license requires author verification before any training use. Parser implementation is a prerequisite before any Layer 2 metadata or enrichment-derived labels are available.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~3,400 | ~80% split, unverified |
| Val   | — | No val split documented |
| Test  | ~860 | ~20% split, unverified |
| OOD   | — | Not applicable |

**Ground Truth**: Image-level quality scores (MOS or objective metrics — annotation method unverified); provenance tier is Tier 1 if human MOS, Tier 2 if computed; annotator details and IAA not documented. All ~4,260 images have quality scores per Section 2.7.

**L2 Metadata**: Not yet available.

### realdae

RealDAE serves as the primary real-world source for camera_smartphone capture method labels (SIG-G5-1) and shadow degradation examples (SIG-G5-2), with 100% of 583 samples confirmed as camera-captured after Layer 2 audit correction (D08). The dataset is research-only licensed and small (600 pairs), so it functions as a secondary or validation source for most IQA heads rather than a primary training source; its chief value is providing pixel-aligned degraded/GT pairs that enable computing PSNR/SSIM quality signals for blur, contrast, and noise heads without MOS scores. Note that the KI-009 known issue (paper claims English-only but 76% is Chinese) means script_cls labels must be sourced from L2 enrichment rather than documentation.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 900 | 450 pairs across 3 tasks |
| Val   | — | No validation split provided |
| Test  | 300 | 150 pairs across 3 tasks |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Paired GT (Tier 0 — Exact): each degraded camera-captured input image (_in.jpg) is paired pixel-aligned with a flatbed-scanner ground truth image (_gt.jpg); manually enhanced by dataset authors (Zhang et al., South China University of Technology).

**L2 Metadata**: Available — 583 total samples (input images only; GT images intentionally excluded). Key fields: domain (EDU 44.8%, PER 10.8%, FIN 9.1%), script_codes (Hans 76.3%, Latn 22.6%, Jpan 0.5%), capture_methods (camera_smartphone 100%), content_flags (has_figure 58.8%, has_table 21.8%, has_handwriting 19.7%).

### rvl-cdip

RVL-CDIP is the **primary large-scale scanner training source and orientation_cls backbone dataset**, with 400K balanced images across 16 document classes providing the broadest layout, domain, and font variety of any real-scan dataset in the corpus. Its confirmed use in stream 4 orientation training (4-rotation scheme) makes it a Primary contributor to MNV4-H1 and SIG-G3-1, while its 100% scanner capture method and authentic 1990s-era degradation make it essential for capture_method_cls and IQA head training. Academic-only license (IIT-CDIP / Legacy Tobacco) prohibits commercial use; the dataset must be excluded from OOD benchmarks to prevent training leakage.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 320,000 | Official only; not in local subset |
| Val   | 40,000 | Official only; not in local subset |
| Test  | 40,000 | Official only; not in local subset |
| OOD   | — | No OOD split; training leakage risk noted |

**Ground Truth**: Image-level document class labels (16 categories, IDs 0–15) assigned by human expert annotation from the IIT-CDIP / Legacy Tobacco collection; Tier 1 provenance with 100% label coverage and perfectly balanced 25,000 samples per class in the official 400K release.

**L2 Metadata**: Available — 16,000 total samples (local 4% subset). Key fields: domain (COM 31.2%, GOV 31.2%, FIN 12.5%), script_codes (Latn 95.5%, Hant 3.1%, Hans 0.8%), capture_methods (scanner 100%), content_flags (has_formula 78.7%, has_figure 8.4%, has_handwriting 6.2%).

### salami

SALAMI is the gold-standard calibration anchor for handwriting legibility assessment heads (SIG-G4-2, SIG-G4-5), providing the only multi-expert pixel-level legibility ground truth in the corpus. With 20 expert assessors providing 4,811 region-level ratings across 250 manuscripts in 7 script families (Cyrl, Latn, Grek, Arab, Armn, Goth, Geor), it enables reliable calibration of legibility regression and classification models. Despite its small size (250 images), its 20-expert consensus maps serve an outsized role as the confidence anchor for all other legibility scores. 15 images (Armn/Goth/Geor, 5 each) are permanently reserved for OOD evaluation. CC-BY-4.0 permits commercial training.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~235 | 250 total minus 15 OOD-reserved |
| Val   | — | No val split defined |
| Test  | — | Used as calibration anchor |
| OOD   | 15 | 5 Armn + 5 Goth + 5 Geor permanently reserved |

**Ground Truth**: Human expert annotation (20 trained assessors); Tier 0 (Exact) provenance via multi-expert consensus. 5-level legibility scale (0–20% through 80–100% readable), 4,811 region-level assessments with bounding boxes, pre-computed pixel-level mean and std maps. 100% coverage.

**L2 Metadata**: Not yet available.

### sd7k

SD7K is the primary and largest contributor to the `shadow_reg` head (SIG-G5-2) and a key contributor to `capture_method_cls` (SIG-G5-1), providing 7,239 camera-captured document pairs across 30+ occluder types and 350+ base documents — the most shadow-diverse document dataset available. Shadow severity labels must be derived from the paired GT using pixel-difference metrics (PSNR/SSIM) since no direct 0-1 severity field exists in the source; this derivation is reliable given the high-quality paired structure and should be completed via `label_shadow_severity.py` before final `shadow_reg` training data assembly. The training count mismatch (6,479 input vs 6,478 target) requires handling of one unpaired sample. License is unspecified; verify with University of Macau (CXH-Research) before non-research deployment.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 6,479 | Input images; 6,478 target (1 unpaired) |
| Val   | — | No validation split provided |
| Test  | 760 | Input/target pairs, ~10% of total |
| OOD   | — | Not applicable |

**Ground Truth**: Paired GT (Tier 0 — Exact). Shadow-degraded input images are paired with shadow-free target images captured under controlled conditions using 30+ real-world occluder types; pairing is implicit via directory structure (no separate annotation files).

**L2 Metadata**: Available — 7,239 total samples. Key fields: domain (GENERAL: 100%), script_codes (Latn: 100%), capture_methods (camera_smartphone: 100%), content_flags (none populated — all unknown).

### signatr6k

SignaTR6K is a narrow, high-purity corpus for the handwriting detection group (G4). Its primary role is as a **DOMINANT-class anchor** for `handwriting_presence_cls` (G4-1) and as a definitive **CURSIVE** content-type example for `handwriting_content_type_cls` (G4-3). Every image is a pure handwritten signature, making this one of the few datasets that provides a clean 1.0 ground truth for `presence_reg` (G4-4) without any mixed-content ambiguity.

The dataset is useful for `capture_method_cls` (SIG-G5-1) as a verified SCANNER class contributor, confirmed by L2 aggregates showing 100% scanner_flatbed capture. However, its utility is intentionally limited: signatures are isolated crops rather than full-page documents, so orientation, skew, layout, shadow, warping, and IQA quality heads are not applicable or only marginally useful.

**License constraint**: Academic use only (research, non-commercial). This restricts its inclusion in any commercially deployed training pipeline. All 12,514 samples must be flagged as research-only in the training manifest.

**Benchmark protection**: No reserved benchmark splits — full dataset available for training, but the academic license takes precedence over split usage. Cross-dataset leakage risk is low (unique domain and content type).

**Synthetic cap note**: Not applicable; dataset is entirely real scanned signatures (0% synthetic). No mixing cap constraints apply, though the narrow domain means overrepresentation risk for the CURSIVE class if not balanced against broader cursive handwriting sources (e.g., IAM, Muharaf).

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | Pre-defined split; per-split count not documented |
| Val   | Unknown | Pre-defined split; per-split count not documented |
| Test  | Unknown | Pre-defined split; per-split count not documented |
| OOD   | — | No OOD split; full 12,514 images across three splits |

**Ground Truth**: Human expert annotation; folder-structure-based split labels (train/val/test) and per-image signer ID. No bounding boxes or segmentation masks — classification-only. Provenance Tier 1 (Annotation); annotator details need verification.

**L2 Metadata**: Available — 12,514 total samples. Key fields: domain (PER: 100%), script_codes (Latn: 100%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 100%, has_signature: 100%).

### signverod

SignverOD provides 2,765 scanned government/contract document images with COCO-style bounding box annotations for 4 categories: signatures (5,044), initials (1,163), redactions (2,308), and dates (700). It is a primary contributor to SIG-G4-1 (handwriting_presence_cls) for signature/initial presence detection in mixed typed+handwritten documents. The bounding box annotations enable spatial handwriting localization training. CC0-1.0 (Public Domain) license imposes zero restrictions.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 1,939 | 7,549 annotation entries |
| Val   | — | No val split defined |
| Test  | 354 | 1,666 annotation entries |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Human annotation (Victor Dibia); Tier 1 provenance. Normalized COCO-style bounding boxes in CSV with 4 categories (signature, initials, redaction, date). 9,215 total annotations. 100% coverage.

**L2 Metadata**: Not yet available.

### siw13

SIW-13 is a secondary contributor to SIG-G2-1 (script_cls), providing the only camera-captured real-world scene text for Tibetan (1,177) and Hebrew (1,242), scripts that are sparsely represented elsewhere; it also contributes Mongolian (1,192) samples which are OOD-excluded at inference but useful for boundary robustness training. The capture_method aggregate (scanner_flatbed) is a known metadata error — the IQA Profile and paper confirm Google Street View camera capture. Research-only license limits use to non-commercial training pipelines.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 12,992 | 8,055 documents, line-level crops |
| Val   | — | No validation split provided |
| Test  | 3,299 | 2,853 documents, line-level crops |
| OOD   | — | No separate OOD split |

**Ground Truth**: Script class labels (13 scripts) annotated by human experts at competition grade; 100% coverage across all 16,291 images. Provenance Tier 1 (human-labeled).

**L2 Metadata**: Available — 16,291 total samples. Key fields: domain (UNK: 100%), script_codes (Thai 13.6%, Kore 9.6%, Hans 8.0%, Hebr 7.6%, Latn 7.5%, Jpan 7.5%, Mong 7.3%, Tibt 7.2%, Khmr 6.6%, Cyrl 6.3%, Knda 6.3%, Arab 6.2%, Grek 6.2%), capture_methods (scanner_flatbed: 100% — NOTE: this is a known metadata error; IQA Profile confirms 100% camera/Google Street View), content_flags (none populated).

### smartdoc-qa

SmartDoc-QA is a **benchmark-only dataset** designed for evaluating IQA methods via OCR accuracy as proxy quality score; training on this dataset is explicitly prohibited (see §7 and §8). Despite having 4,260 camera-smartphone images with controlled single/multiple distortions, the robotic-arm capture environment and benchmark-design intent make it unsuitable for augmenting training distributions. The dataset resides at `02_benchmark_only/smartdoc-qa/` and should only be used for post-training evaluation of capture method, IQA, and warping head performance on mobile-captured documents.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | No official splits defined |
| Val   | — | No official splits defined |
| Test  | — | No official splits defined |
| OOD   | 4,260 | All splits — benchmark-only |

**Ground Truth**: Human expert annotation (Tier 1) by L3i Lab, Université de La Rochelle; labels cover distortion type/amount, OCR accuracy (3 engines), and 8,498 QA pairs on mobile-captured documents captured via robotic arm.

**L2 Metadata**: Available — 4,260 total samples. Key fields: domain (GENERAL 55.8%, ADM 15.4%, FIN 13.4%), script_codes (Latn 93.1%, Beng 2.6%, Hant 2.4%), capture_methods (camera_smartphone 100%), content_flags (has_figure 54.3%, has_table 7.4%).

### sroie

SROIE contributes 973 real-world camera/scanner receipt images to the Latin-script and IQA training pools, providing authentic thermal-print degradation patterns (low contrast, fading, glare) not well represented in document datasets. License is unverified (Research Use Only conservative classification) — confirm before including in commercial training runs. The 347-image test split is competition held-out and should be treated as OOD evaluation material, not training data.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 626 | Verified; Malaysian receipts, camera/scanner |
| Val   | — | No val split in official release |
| Test  | 347 | Competition held-out; treat as OOD eval |
| OOD   | 347 | Test split is competition benchmark held-out |

**Ground Truth**: Human-annotated by ICDAR 2019 competition annotators; Tier 1 provenance. All 973 receipt images carry quad-coordinate text regions with transcriptions plus four key-entity labels (company, date, address, total). 100% GT coverage verified against HuggingFace rth/sroie-2019-v2.

**L2 Metadata**: Available — 973 total samples. Key fields: domain (FIN: 100%), script_codes (Latn: 100%), capture_methods (camera_smartphone: 100%), content_flags (has_table: 30.6%, has_figure: 11.7%, has_formula: 0.2%).

### staindoc

StainDoc's primary contribution to the unified training corpus is as a `capture_method=camera_smartphone` anchor for the SIG-G5-1 head, providing ~5,000 confirmed camera-captured real-world documents. As a paired stained/clean correction dataset, it also offers SSIM-derivable overall_quality labels useful for SIG-G1-6 training, and represents the stain/bleed-through degradation class that is underrepresented in most IQA datasets. The dataset is restricted to research use pending parser implementation; the MIT license permits broad use but the parser must be built before L2 metadata and training manifests can be generated.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~4,000 | Stained/clean paired; camera-captured |
| Val   | — | No validation split documented |
| Test  | ~1,000 | Stained/clean paired; ~20% holdout |
| OOD   | — | Not a benchmark-only dataset |

**Ground Truth**: Paired image structure (Tier 0 Exact) — clean reference images captured alongside stained inputs, matched by filename; no human annotators required. Every stained image has a 1:1 clean GT counterpart with 100% pairing coverage.

**L2 Metadata**: Not yet available.

### synth-multiscript-v3

synth-multiscript-v3 is the primary synthetic training dataset, providing 190,485 GCS-confirmed images across 27 ISO 15924 scripts and 198 languages with comprehensive Layer 2 v2.3 metadata. It serves as the dominant contributor to SIG-G2-1 (script_cls) and the single base from which all synthetic task-specific views are derived (orientation, skew, resolution quality, IQA, shadow, warping). Images are stored pristine (no degradation baked in) with full generation provenance and reproducible degradation parameters in JSON sidecars. **P0 blocker**: Arab script is at 3.8x its target budget (49K vs 13K cap) and 17 scripts are below their minimum floor — rebalancing required before training. MIT license permits commercial use.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~152,388 | 80% estimate; SHA256-keyed splits.jsonl at GCS root |
| Val   | ~19,049 | 10% estimate |
| Test  | ~19,049 | 10% estimate |
| OOD   | — | OOD scripts handled separately via SALAMI |

**Ground Truth**: Synthetic exact (Tier 0) provenance. Per-image JSON sidecars contain: orientation_class (0/90/180/270), skew_angle_degrees, 8 IQA dimension scores, resolution_quality_score, text_direction (ltr/rtl/ttb), script codes, language codes, layout type, quality tier, color mode, font families, and degradation seed for reproducible replay. 100% coverage.

**L2 Metadata**: Fully available (v2.3.0 schema, 100% coverage). Key aggregate stats: quality tiers (PRISTINE 10%, HIGH 25%, MEDIUM 35%, LOW 20%, DEGRADED 10%); resolution tiers across 7 DPI levels (72–600); layout types (single_column 64.3%, multi_column 24.9%, form_based 8.2%, complex 2.6%).

### tablebank

TableBank's primary role is as a **BORN_DIGITAL negative pool** for SIG-G5-1 capture_method_cls (~260K labels), a **large handwriting-absence pool** for SIG-G4-1/G4-4, and a **secondary contributor for SIG-G1 IQA heads** as high-quality clean-document reference examples — particularly valuable for compression score (SIG-G1-5) because its JPEG format exposes real grid-line compression artifacts. It is also a **secondary contributor for SIG-G5-4 code_cls** via its LaTeX arXiv subset. License is Apache-2.0 with research-use intent (commercial use requires review). No OOD script exclusions apply — 100% Latin with no non-Latin content.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 260,582 | LaTeX (187,199) + Word (73,383) |
| Val   | 10,000 | LaTeX (7,265) + Word (2,735) |
| Test  | 8,000 | LaTeX (5,719) + Word (2,281) |
| OOD   | — | Training dataset; no OOD split |

**Ground Truth**: Automatic programmatic extraction from LaTeX (arXiv) and Word (MSRA NLC) source documents; Tier 0 provenance (exact, no human annotation required). All 278K images carry table bounding boxes in COCO format.

**L2 Metadata**: Available — 260,025 total samples (train split). Key fields: domain (SCI: 100%), script_codes (Latn: 100%), capture_methods (born_digital: 100%), content_flags (has_table: 100%).

### tibhcr

TibHCR is the **sole large-scale Tibetan (Tibt) script source** in the training corpus, making it indispensable for SIG-G2-1 script classification and G4 handwriting heads despite being character-level rather than document-level. Academic license restricts use to research only, excluding commercial deployment pipelines. Direct use in document-level heads (MNV4-H1, IQA, skew) requires synthetic document compositing — individual characters must be assembled into simulated document pages before contributing orientation or quality training signal.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No official splits provided |
| Val   | — | No official splits provided |
| Test  | Unknown | No official splits provided |
| OOD   | — | All 141,698 images in single undivided pool |

**Ground Truth**: Human expert annotation by 235 Tibetan writers across 5 Chinese provinces; character class labels encoded in directory structure and Tibetan Unicode in label.txt; Tier 1 (Annotation) provenance with 100% GT coverage.

**L2 Metadata**: Available — 141,698 total samples. Key fields: domain (EDU: 100%), script_codes (Tibt: 100%), capture_methods (scanner_flatbed: 100%), content_flags (has_handwriting: 141,698 populated).

### tobacco800

Tobacco800 contributes primarily as a **capture_method/scanner training source and handwriting presence signal**, with its 1,290 authentic archival scans providing genuine real-world degradation patterns (aging, foxing, bleed-through) found nowhere else in the corpus. Its binary-only format restricts applicability to IQA heads that depend on grayscale intensity variation (blur, contrast, shadow, warping) while making it uniquely valuable for binarization artifact representation. Academic-only license prohibits commercial use, and the dataset must be excluded from OOD benchmarks to prevent training leakage.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | No official splits; use cross-validation |
| Val   | — | No official splits; use cross-validation |
| Test  | — | No official splits; use cross-validation |
| OOD   | — | Single unsplit collection of 1,290 images |

**Ground Truth**: Human expert annotations by University of Maryland researchers (Zhu & Doermann, CVPR 2007 / ICDAR 2007), covering bounding boxes for signatures and logos; Tier 1 provenance. Annotations are distributed separately via TC-11 and are not included in the standard dataset distribution.

**L2 Metadata**: Available — 1,290 total samples. Key fields: domain (ADM 47%, LEG 18%, SCI 17%), script_codes (Latn 99.8%, Zyyy 0.2%), capture_methods (scanner_adf 100%), content_flags (has_handwriting 65%, has_figure 77%, has_signature 64%, has_table 24%).

### vjroda

VJRODa serves exclusively as an OOD evaluation set for Japanese vertical text (tategaki), providing ~100 real-world government PDF pages rendered at 150 DPI. At only 100 images it is too small for training but provides critical real-world validation samples for SIG-G2-1 (script_cls) and SIG-G3-1 (orientation_cls) that complement JSSODa's synthetic vertical text. Its born-digital origin means it contributes no IQA training signal. CC-BY-4.0 permits unrestricted use.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | — | Not used for training (too small) |
| Val   | — | No val split defined |
| Test  | ~100 | Full dataset used as OOD evaluation |
| OOD   | ~100 | Entire dataset designated for Jpan vertical text OOD eval |

**Ground Truth**: Human annotation (text transcriptions with structural tags — header/footer/caption); Tier 1 provenance from LLM-JP / National Institute of Informatics. Text direction is 100% vertical (tategaki). 100% coverage.

**L2 Metadata**: Audited 2026-02-25 (18 samples). Key findings: capture_method should be born_digital (not scanner), has_handwriting=false, domain_level1=ADM. Only 18 of ~100 images downloaded.

### warpdoc

WarpDoc serves as the primary labeled source for the `warping_reg` head (SIG-G5-3) and `capture_method_cls` head (SIG-G5-1), providing 1,020 camera-captured documents with 6 controlled geometric distortion types. Its chief constraint is the absence of continuous warping severity scores — the distortion class labels (Fold/Curved/Perspective/etc.) must be converted to a 0-1 severity proxy, likely via pixel-wise difference between warped input and the digital GT extension, before this dataset can contribute hard labels to `warping_reg` training. License is unspecified; verify with SG-ViLab before using in any commercial pipeline.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | No formal train split defined |
| Val   | — | No val split defined |
| Test  | 1,020 | Full dataset used as benchmark |
| OOD   | — | Not designated as OOD |

**Ground Truth**: Paired GT at Tier 0 (Exact); distortion type labels derived from directory structure (6 categories: Fold, Curved, Incomplete, Random, Rotating, Perspective) created by SG-ViLab for CVPR 2022; digital GT counterparts added June 2022 but pairing is unverified.

**L2 Metadata**: Available — 1,020 total samples. Key fields: domain (GENERAL: 100%), script_codes (Latn: 100%), capture_methods (camera_smartphone: 100%), content_flags (none populated).

### wili-2018

WiLI-2018 is a **text-only corpus** (235K Wikipedia paragraphs across 235 languages) with no image component, making it incompatible with all 22 visual training heads. Its only potential contribution to the pipeline would be as a text source for synthetic document generation, but this role is fully and preferably served by OpenLID-v2 — which additionally provides the ISO 15924 script codes required for font selection. The dataset is classified as blocked and superseded with no active integration path; do not download or integrate.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | 118,000 | Wikipedia paragraphs; ISO 639-3 language labels |
| Val   | — | No validation split provided in source dataset |
| Test  | 117,000 | Wikipedia paragraphs; ISO 639-3 language labels |
| OOD   | — | Text corpus only — no images; not applicable to visual pipeline |

**Ground Truth**: Language labels are automatically extracted from Wikipedia metadata (ISO 639-3 codes), one label per paragraph with 100% coverage. Provenance tier: Tier 1 (Automatic Extraction); no human annotation or crowdsourcing involved.

**L2 Metadata**: Not yet available.

### wsrd

WSRD is a primary contributor to the `shadow_reg` head (SIG-G5-2) and `capture_method_cls` head (SIG-G5-1), providing ~1,200 paired shadow/shadow-free document images from the NTIRE 2023/2024 challenge benchmark. Shadow severity scores must be derived from the paired GT via pixel-difference metrics (e.g., PSNR/SSIM) since no direct 0-1 severity label is provided; this derivation is straightforward given the high-quality paired structure. The dataset is smaller than SD7K (~1,200 vs ~7,239 pairs) but offers a pre-split train/val/test structure and established NTIRE benchmark credentials. License is unspecified (NTIRE challenge terms may apply); verify with challenge organizers before non-research use.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | ~1,000 | Paired shadow/shadow-free images |
| Val   | ~100 | Paired shadow/shadow-free images |
| Test  | ~100 | GT may be withheld (NTIRE challenge) |
| OOD   | — | No OOD split defined |

**Ground Truth**: Paired image structure — each shadow-degraded input is paired with a pixel-aligned shadow-free target image captured under the same conditions. Annotation provenance is Tier 0 (Exact); 100% GT label coverage via directory-based shadow/clean pairing from the NTIRE 2023/2024 challenge benchmark.

**L2 Metadata**: Available — 4,500 total samples. Key fields: domain (GENERAL: 100%), script_codes (Latn: 100%), capture_methods (camera_smartphone: 100%), content_flags (none populated).

### yarmouk

Yarmouk is a primary contributor to SIG-G4 (handwriting) heads as the largest Arabic-script handwritten document dataset in the pool (15,062 pages), pairing well with muharaf and pucit-ohul for Arab-script handwriting diversity across formal and informal registers. The has_handwriting=True flag covers all samples though a printed-only subset likely exists — VLM review is recommended before using for binary handwriting-presence training. Research-only license from Yarmouk University; not cleared for commercial deployment.

**Data Profile**:

| Split | Count | Notes |
|-------|-------|-------|
| Train | Unknown | "training sample/" folder; page counts not documented |
| Val   | — | No val split defined in source |
| Test  | Unknown | "testing sample/" folder; page counts not documented |
| OOD   | — | Not applicable |

**Ground Truth**: Human expert annotation providing paired HTML annotations (6,061 files) and plain-text OCR transcriptions (4,633 of 6,039 PDFs); Tier 1 annotation provenance from Yarmouk University researchers.

**L2 Metadata**: Not yet available.

---

## Coverage Statistics

**MNV4-H1 — orientation_cls (MNV4)**

- Primary contributors (6): bhutan-afs, invoices-kg, jssoda, midv2020, rvl-cdip, sroie
- Secondary contributors (20): arabic-docs, docsynth, funsd, funsd-plus, iam, indicdlp, mle2e, mlt19, multimodal-textbook, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, pucit-ohul, realdae, sd7k, tibhcr, warpdoc, wsrd, yarmouk
- Negatives only (18): casia-hwdb2, cc-ocr, cocotext, cvsi, doclaynet, fintabnet, hiertext, hindi-synth, im2latex, mdiw13, midv500, nist-sd2, omnidocbench, pubtabnet, signatr6k, siw13, tablebank, tobacco800

**MNV4-H2 — skew_reg (MNV4)**

- Primary contributors (0): none
- Secondary contributors (14): arabic-docs, funsd, funsd-plus, iam, indicdlp, mle2e, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, pucit-ohul, rvl-cdip, sroie, yarmouk
- Negatives only (18): bhutan-afs, casia-hwdb2, cc-ocr, cvsi, doclaynet, docsynth, fintabnet, hiertext, hindi-synth, im2latex, jssoda, mdiw13, multimodal-textbook, nist-sd2, pubtabnet, siw13, tablebank, tobacco800

**MNV4-H3 — resolution_quality_reg (MNV4)**

- Primary contributors (1): bhutan-afs
- Secondary contributors (37): arabic-docs, casia-hwdb2, cc-ocr, cocotext, cvsi, doclaynet, docreal, docsynth, drccbi, fintabnet, funsd, funsd-plus, hiertext, hindi-synth, iam, im2latex, indicdlp, invoices-kg, markushgrapher, mle2e, muharaf, multimodal-textbook, multilingual-scripts, nist-sd19, nist-sd2, nist-sd6, ocr-quality, q-doc, realdae, rvl-cdip, signatr6k, siw13, sroie, staindoc, tablebank, tobacco800, yarmouk
- Negatives only (7): iiit-hw-hindi, jssoda, kuzushiji, mdiw13, mlt19, omnidocbench, pubtabnet

**SIG-G1-1 — blur_score**

- Primary contributors (7): arabic-docs, cvsi, funsd, funsd-plus, mle2e, midv500, sroie
- Secondary contributors (33): anyphotodoc6300, casia-hwdb2, casia-hwdb2-line, cc-ocr, cocotext, doclaynet, docreal, docsynth, drccbi, hiertext, hindi-synth, iam, im2latex, indicdlp, khatt, markushgrapher, midv2020, muharaf, multimodal-textbook, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, q-doc, realdae, rvl-cdip, signatr6k, siw13, staindoc, tablebank, tobacco800, warpdoc, yarmouk
- Negatives only (16): bhutan-afs, fintabnet, hasy, iiit-hw-hindi, invoices-kg, jssoda, kuzushiji, mdiw13, mlt19, nist-sd2, omnidocbench, pubtabnet, pucit-ohul, sd7k, tibhcr, wsrd

**SIG-G1-2 — noise_score**

- Primary contributors (7): arabic-docs, funsd, funsd-plus, mle2e, midv500, rvl-cdip, sroie
- Secondary contributors (35): anyphotodoc6300, casia-hwdb2, casia-hwdb2-line, cc-ocr, cocotext, cvsi, doclaynet, docreal, docsynth, drccbi, hiertext, hindi-synth, iam, im2latex, indicdlp, khatt, markushgrapher, midv2020, muharaf, multimodal-textbook, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, q-doc, realdae, sd7k, signatr6k, siw13, staindoc, tablebank, tobacco800, warpdoc, wsrd, yarmouk
- Negatives only (14): bhutan-afs, fintabnet, hasy, iiit-hw-hindi, invoices-kg, jssoda, kuzushiji, mdiw13, mlt19, nist-sd2, omnidocbench, pubtabnet, pucit-ohul, tibhcr

**SIG-G1-3 — contrast_score**

- Primary contributors (10): arabic-docs, bhutan-afs, funsd, funsd-plus, mle2e, midv2020, midv500, sd7k, sroie, wsrd
- Secondary contributors (33): anyphotodoc6300, casia-hwdb2, casia-hwdb2-line, cc-ocr, cocotext, cvsi, doclaynet, docreal, docsynth, drccbi, fintabnet, hiertext, hindi-synth, iam, im2latex, indicdlp, invoices-kg, khatt, markushgrapher, muharaf, multimodal-textbook, multilingual-scripts, nepali-handwritten, q-doc, realdae, rvl-cdip, signatr6k, siw13, staindoc, tablebank, tobacco800, warpdoc, yarmouk
- Negatives only (12): iiit-hw-hindi, jssoda, kuzushiji, mdiw13, mlt19, nist-sd19, nist-sd2, nist-sd6, omnidocbench, pubtabnet, pucit-ohul, tibhcr

**SIG-G1-4 — skew_score**

- Primary contributors (0): none
- Secondary contributors (15): arabic-docs, casia-hwdb2, casia-hwdb2-line, funsd, funsd-plus, iam, indicdlp, mle2e, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, rvl-cdip, sroie, yarmouk
- Negatives only (20): bhutan-afs, cc-ocr, cvsi, doclaynet, docsynth, fintabnet, hiertext, hindi-synth, iiit-hw-hindi, im2latex, jssoda, mdiw13, mlt19, multimodal-textbook, nist-sd2, pubtabnet, pucit-ohul, siw13, tablebank, tobacco800

**SIG-G1-5 — compression_score**

- Primary contributors (6): cvsi, mle2e, midv2020, midv500, multimodal-textbook, sroie
- Secondary contributors (21): arabic-docs, casia-hwdb2, casia-hwdb2-line, cc-ocr, cocotext, doclaynet, docsynth, fintabnet, funsd, funsd-plus, hiertext, im2latex, indicdlp, invoices-kg, khatt, markushgrapher, multilingual-scripts, rvl-cdip, siw13, tablebank, yarmouk
- Negatives only (13): bhutan-afs, iam, iiit-hw-hindi, jssoda, kuzushiji, mdiw13, mlt19, nepali-handwritten, nist-sd2, omnidocbench, pubtabnet, pucit-ohul, tibhcr

**SIG-G1-6 — overall_quality**

- Primary contributors (10): arabic-docs, bhutan-afs, funsd, funsd-plus, midv2020, midv500, ocr-quality, q-doc, rvl-cdip, sroie
- Secondary contributors (33): anyphotodoc6300, casia-hwdb2, casia-hwdb2-line, cc-ocr, cvsi, docalign12k, doclaynet, docreal, docsynth, drccbi, fintabnet, hiertext, hindi-synth, iam, im2latex, indicdlp, invoices-kg, khatt, markushgrapher, mle2e, muharaf, multimodal-textbook, multilingual-scripts, nist-sd19, nist-sd6, sd7k, siw13, staindoc, tablebank, tobacco800, warpdoc, wsrd, yarmouk
- Negatives only (7): iiit-hw-hindi, jssoda, mdiw13, mlt19, nist-sd2, omnidocbench, pubtabnet

**SIG-G2-1 — script_cls**

- Primary contributors (31): arabic-docs, bhutan-afs, casia-hwdb2, casia-hwdb2-line, cc-ocr, cvsi, fintabnet, funsd, funsd-plus, hiertext, hindi-synth, indicdlp, invoices-kg, jssoda, kuzushiji, mdiw13, mle2e, midv2020, midv500, mlt19, muharaf, multimodal-textbook, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, pucit-ohul, siw13, sroie, tibhcr, yarmouk
- Secondary contributors (16): cocotext, doclaynet, docreal, docsynth, dzongkha-digits, iam, iiit-hw-hindi, im2latex, khatt, nist-sd2, ocr-quality, omnidocbench, pubtabnet, realdae, rvl-cdip, tablebank
- Negatives only (6): anyphotodoc6300, sd7k, signatr6k, tobacco800, warpdoc, wsrd

**SIG-G3-1 — orientation_cls (post)**

- Primary contributors (6): bhutan-afs, invoices-kg, jssoda, midv2020, rvl-cdip, sroie
- Secondary contributors (20): arabic-docs, docsynth, funsd, funsd-plus, iam, indicdlp, mle2e, mlt19, multimodal-textbook, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, pucit-ohul, realdae, sd7k, tibhcr, warpdoc, wsrd, yarmouk
- Negatives only (18): casia-hwdb2, cc-ocr, cocotext, cvsi, doclaynet, fintabnet, hiertext, hindi-synth, im2latex, mdiw13, midv500, nist-sd2, omnidocbench, pubtabnet, signatr6k, siw13, tablebank, tobacco800

**SIG-G3-2 — skew_reg (post)**

- Primary contributors (0): none
- Secondary contributors (12): arabic-docs, funsd, funsd-plus, iam, indicdlp, mle2e, multilingual-scripts, nist-sd19, nist-sd6, rvl-cdip, sroie, yarmouk
- Negatives only (17): bhutan-afs, casia-hwdb2, cc-ocr, cvsi, doclaynet, fintabnet, hiertext, hindi-synth, im2latex, jssoda, mdiw13, multimodal-textbook, nist-sd2, pubtabnet, siw13, tablebank, tobacco800

**SIG-G4-1 — handwriting_presence_cls**

- Primary contributors (28): arabic-docs, bhutan-afs, casia-hwdb2, casia-hwdb2-line, cc-ocr, cocotext, cvsi, docsynth, funsd, hiertext, hindi-synth, iam, im2latex, indicdlp, kuzushiji, markushgrapher, muharaf, multimodal-textbook, multilingual-scripts, nepali-handwritten, nist-sd19, nist-sd6, pucit-ohul, signatr6k, siw13, tibhcr, tobacco800, yarmouk
- Secondary contributors (10): dzongkha-digits, funsd-plus, hasy, iiit-hw-hindi, khatt, mdiw13, nist-sd2, omnidocbench, rvl-cdip, sroie
- Negatives only (20): anyphotodoc6300, doc3d, docalign12k, doclaynet, docreal, drccbi, fintabnet, invoices-kg, mle2e, midv2020, midv500, ocr-quality, pubtabnet, q-doc, realdae, sd7k, staindoc, tablebank, warpdoc, wsrd

**SIG-G4-2 — handwriting_legibility_cls**

- Primary contributors (9): bhutan-afs, cocotext, hiertext, iam, muharaf, multimodal-textbook, nist-sd19, nist-sd6, tibhcr
- Secondary contributors (17): arabic-docs, casia-hwdb2, casia-hwdb2-line, dzongkha-digits, funsd, funsd-plus, hasy, iiit-hw-hindi, khatt, kuzushiji, nepali-handwritten, nist-sd2, pucit-ohul, rvl-cdip, signatr6k, tobacco800, yarmouk
- Negatives only (4): indicdlp, invoices-kg, mle2e, sroie

**SIG-G4-3 — handwriting_content_type_cls**

- Primary contributors (15): bhutan-afs, casia-hwdb2, casia-hwdb2-line, hasy, iam, kuzushiji, muharaf, multimodal-textbook, nepali-handwritten, nist-sd19, nist-sd6, pucit-ohul, signatr6k, tibhcr, yarmouk
- Secondary contributors (10): arabic-docs, dzongkha-digits, funsd, funsd-plus, hiertext, iiit-hw-hindi, khatt, nist-sd2, rvl-cdip, tobacco800
- Negatives only (5): cocotext, indicdlp, invoices-kg, mle2e, sroie

**SIG-G4-4 — presence_reg**

- Primary contributors (21): arabic-docs, bhutan-afs, casia-hwdb2, casia-hwdb2-line, cc-ocr, cvsi, docsynth, funsd, hiertext, iam, kuzushiji, markushgrapher, muharaf, multilingual-scripts, nepali-handwritten, nist-sd19, pucit-ohul, signatr6k, siw13, tibhcr, yarmouk
- Secondary contributors (13): cocotext, dzongkha-digits, funsd-plus, iiit-hw-hindi, indicdlp, khatt, mdiw13, multimodal-textbook, nist-sd2, nist-sd6, rvl-cdip, sroie, tobacco800
- Negatives only (19): anyphotodoc6300, doc3d, docalign12k, doclaynet, docreal, drccbi, fintabnet, hasy, invoices-kg, mle2e, midv2020, midv500, pubtabnet, q-doc, sd7k, staindoc, tablebank, warpdoc, wsrd

**SIG-G4-5 — legibility_reg**

- Primary contributors (4): bhutan-afs, hiertext, iam, tibhcr
- Secondary contributors (21): arabic-docs, casia-hwdb2, casia-hwdb2-line, cocotext, dzongkha-digits, funsd, funsd-plus, hasy, iiit-hw-hindi, khatt, kuzushiji, muharaf, nepali-handwritten, nist-sd19, nist-sd2, nist-sd6, pucit-ohul, rvl-cdip, signatr6k, tobacco800, yarmouk
- Negatives only (4): invoices-kg, mle2e, multimodal-textbook, sroie

**SIG-G5-1 — capture_method_cls**

- Primary contributors (44): anyphotodoc6300, arabic-docs, bhutan-afs, casia-hwdb2, casia-hwdb2-line, cocotext, cvsi, docalign12k, doclaynet, docreal, drccbi, fintabnet, funsd, funsd-plus, hiertext, iam, im2latex, indicdlp, invoices-kg, mdiw13, mle2e, midv2020, midv500, mlt19, muharaf, multimodal-textbook, nepali-handwritten, nist-sd19, nist-sd6, pubtabnet, pucit-ohul, realdae, rvl-cdip, sd7k, signatr6k, siw13, sroie, staindoc, tablebank, tibhcr, tobacco800, warpdoc, wsrd, yarmouk
- Secondary contributors (6): dzongkha-digits, hasy, khatt, kuzushiji, nist-sd2, q-doc
- Negatives only (5): cc-ocr, doc3d, iiit-hw-hindi, multilingual-scripts, omnidocbench

**SIG-G5-2 — shadow_reg**

- Primary contributors (3): realdae, sd7k, wsrd
- Secondary contributors (17): anyphotodoc6300, arabic-docs, cvsi, docalign12k, docreal, drccbi, funsd, funsd-plus, hiertext, mle2e, midv2020, midv500, nepali-handwritten, q-doc, siw13, sroie, staindoc
- Negatives only (13): bhutan-afs, cc-ocr, doclaynet, fintabnet, iam, invoices-kg, mlt19, multimodal-textbook, multilingual-scripts, nist-sd2, pubtabnet, tablebank, yarmouk

**SIG-G5-3 — warping_reg**

- Primary contributors (6): anyphotodoc6300, doc3d, docalign12k, docreal, drccbi, warpdoc
- Secondary contributors (6): arabic-docs, mle2e, nepali-handwritten, q-doc, realdae, sroie
- Negatives only (19): bhutan-afs, cc-ocr, cvsi, doclaynet, fintabnet, funsd, funsd-plus, hiertext, iam, invoices-kg, mlt19, multimodal-textbook, multilingual-scripts, nist-sd2, pubtabnet, siw13, staindoc, tablebank, yarmouk

**SIG-G5-4 — code_cls**

- Primary contributors (4): cvsi, im2latex, siw13, yarmouk
- Secondary contributors (8): cc-ocr, doclaynet, docsynth, hiertext, indicdlp, multimodal-textbook, omnidocbench, tablebank
- Negatives only (11): bhutan-afs, cocotext, docreal, fintabnet, funsd, funsd-plus, iam, nist-sd2, pubtabnet, q-doc, realdae

**SIG-G5-5 — resolution_quality_reg (SigLIP)**

- Primary contributors (2): bhutan-afs, q-doc
- Secondary contributors (36): arabic-docs, casia-hwdb2, cc-ocr, cocotext, cvsi, doclaynet, docreal, docsynth, drccbi, fintabnet, funsd, funsd-plus, hiertext, hindi-synth, iam, im2latex, indicdlp, invoices-kg, markushgrapher, mle2e, muharaf, multimodal-textbook, multilingual-scripts, nist-sd19, nist-sd2, nist-sd6, ocr-quality, realdae, rvl-cdip, signatr6k, siw13, sroie, staindoc, tablebank, tobacco800, yarmouk
- Negatives only (7): iiit-hw-hindi, jssoda, kuzushiji, mdiw13, mlt19, omnidocbench, pubtabnet

---

## Changelog

| Version | Date | Notes |
| ------- | ---- | ----- |
| 1.0.0 | 2026-02-24 | Created skeleton with Section 1 (head requirements digest) and Section 2 (empty grids for all 69 datasets × 22 heads). Template updated to v1.6.0. |
| 1.0.2 | 2026-02-24 | Fixed khatt ❓ markers; standardized Section 13 headings to ## format across all 69 source files; regenerated all grids and statistics. |
| 1.0.1 | 2026-02-24 | Populated all grids, Section 3 per-dataset summaries, and coverage statistics via aggregate_head_coverage.py aggregation script. |
