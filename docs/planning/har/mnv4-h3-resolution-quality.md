# Head Adequacy Review: resolution_quality (MNV4-H3)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: D — Resolution
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Specification

| Field | Value |
| --- | --- |
| Head ID | MNV4-H3 |
| Model | MobileNetV4-Conv-S |
| Group | Pre-Correction Stage Gate |
| Head Name | resolution_quality |
| Task Type | Regression 0-1 (char-height-aware quality score) |
| Output Format | Linear output [0-1] |
| Priority | P0 |
| Performance Target | MAE < 0.1 |
| Primary L2 Field | `resolution.resolution_quality_score` (0-1) |
| Shared-Data Heads | SIG-G5-5 (resolution_quality_reg uses same training dataset — validation head) |
| Training Phase | Phase 4 — Pre-Correction Gate (trained before SigLIP 2) |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `resolution.resolution_quality_score` _(float 0-1, char-height-aware)_

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better)

**Label Provenance**: tier_0_exact (PaddleOCR DBNet + CC analysis pipeline — automated measurement)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/ for DIQA-5000 and OHR-Bench resolution labeling defects)_

### Candidate Source Datasets

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | ✅ Complete | 99.9% (5,499 labeled, 1 error) | _(analysis required)_ | _(check audit)_ | ~5,499 |
| OHR-Bench | 8,500 | _(analysis required)_ | — | — | — | — |
| RealDAE | 1,200 | _(analysis required)_ | — | — | — | — |
| DocLayNet (multi-DPI renders) | _(analysis required)_ | _(not populated)_ | 0% | — | — | 0 (needs rendering pipeline) |
| RVL-CDIP (multi-DPI renders) | _(analysis required)_ | _(not populated)_ | 0% | — | — | 0 (needs rendering pipeline) |

### Usable Pool Summary

- **Total usable before enrichment**: ~5,499 (DIQA-5000 only)
- **Training target**: 30,000 images
- **Gap**: ~24,500 images (requires OHR-Bench labeling + multi-DPI rendering pipeline)

### VLM Validation Sampling Tier

_(analysis required — char-height pipeline is automated; VLM not used for resolution_quality labels; sampling tier applies to audit validation only)_

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| KI-RQ-01 | PaddleOCR v2 ONLY (paddleocr>=2.7,<3.0) — v3 API completely incompatible; labeling pipeline will silently fail on v3 | HIGH — version pin must be enforced in requirements |
| KI-RQ-02 | SIGILL on Intel Broadwell CPUs: PaddlePaddle CPU path hits illegal instruction (no AVX-512) | MEDIUM — labeling must run on GPU VM (Vultr A100 or equivalent) |
| KI-RQ-03 | V1 precision: median IQR 9.0px (target was 2-3px), 54% cross-bucket rate; coarse buckets validated (KW H=141.6, Cohen's d=0.91) | MEDIUM — V2 strategy planned; coarse label quality sufficient for training |
| KI-RQ-04 | Born-digital low-DPI paradox: large fonts at 72 DPI yield high char_height despite low effective resolution — label may misclassify as high quality | MEDIUM — see OOD-Resolution 6a sub-source |

### Remediation Path

_(analysis required — enumerate steps: 1) run OHR-Bench labeling pipeline on GPU VM, 2) run RealDAE labeling, 3) build multi-DPI rendering pipeline for DocLayNet/RVL-CDIP, 4) validate bucket distribution matches target)_

---

## Section 3 — Training Dataset Targets

| Field | Value |
| --- | --- |
| Target Count | 30,000 images |
| Assembly Status | ⏳ Not started (0/30,000) |
| Current Labeled | DIQA-5000 complete (5,500 images, median char_height=31px, median score=0.525) |
| Distribution Target | ~49% needs_light_upscale / ~37% optimal / ~11% good / ~3% needs_major_upscale |
| Multi-DPI Rendering | Source docs rendered at 72/100/150/200/250/300/400/600 DPI to populate lower-resolution training examples |
| Real Data Ratio | 100% real documents (no synthetic generation — labels derived from actual image measurements) |
| Label Source | Character-height-aware pipeline: PaddleOCR DBNet text detection + CC analysis (two-stage) |
| Assembly Script | `scripts/prepare_multitask_datasets.py` (resolution subcommand not yet implemented) |

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| resolution | `resolution.category` | CRITICAL — this is the core signal for this head; DPI tier must span full range | All 8 DPI tiers (72/100/150/200/250/300/400/600) represented | DIQA-5000 only (natural distribution) | TBD |
| capture_method | `capture_method.method` | HIGH — scanner, camera, and born-digital yield different char_height/DPI relationships | ≥ 3 methods (born_digital, scanner, camera_smartphone) | unknown | TBD |
| script_code | `language.script_code` | HIGH — CJK characters are larger; char_height measurement differs by script | ≥ 3 script families (LATN, HANS/HANT, ARAB) | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs lose fine character structure; pipeline behavior changes | ≥ 2 modes (color/grayscale + binarized) | unknown | TBD |
| domain | `domain.level1` | MEDIUM — document density affects char_height measurement reliability | ≥ 5 domains | unknown | TBD |
| layout_type | `structure.layout_type` | MEDIUM — dense formula/table layouts confound char_height detection | ≥ 3 types | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — aged docs may have ink spread affecting apparent char boundaries | ≥ 2 age classes | unknown | TBD |
| degradation | `quality.degradations` | MEDIUM — blur/noise can affect char_height measurement accuracy | ≥ 3 degradation types | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Born-digital PDF at low DPI (large fonts → high char_height paradox) | `capture_method.method` = born_digital + `resolution.dpi` < 150 | ⚠️ | OOD-Resolution 6a tests this; training data may lack born-digital low-DPI examples |
| Bicubic-upscaled raster (artificially inflated DPI, no real resolution gain) | `resolution.upscale_factor` | ⚠️ | OOD-Resolution 6b tests 2× and 4× upscaling; must confirm labels capture pre-upscale quality |
| CJK documents where char_height is naturally larger | `language.script_code` in {HANS, HANT, JPAN, KORE} | ⏳ | analysis required — DIQA-5000 may be predominantly Latin |
| Documents with no text (image-only pages) | `structure.has_text` = false | ⏳ | PaddleOCR pipeline fails gracefully; label should fall back to DPI-based heuristic |
| Mixed-resolution pages (high-DPI scan of low-DPI photocopy) | _(no specific L2 field)_ | ⏳ | Not representable by single score; label reflects overall page char_height distribution |
| Documents below PaddleOCR detection threshold (very sparse text) | `structure.text_density` | ⏳ | Stage 1 fallback to CC analysis handles sparse text; coverage in DIQA-5000 unknown |

---

## Section 6 — OOD Design

**Primary OOD Category**: OOD-Resolution (Phase 6, P0, 500 total images)

### OOD Sub-Sources

| Sub-Source | Images | Source | Labels Required | Evaluation Stage | Notes |
| --- | --- | --- | --- | --- | --- |
| 6a. Vector PDF at 3 DPIs | 300 | DocLayNet born-digital PDFs rendered at 72/150/300 DPI (100 images each) | resolution_quality_score (measured on rendered image) | mobilenetv4 + siglip2 | Tests born-digital low-DPI paradox: large fonts at 72 DPI → high char_height despite low effective resolution. Must SHA256+pHash dedup against training manifests. Requires separate upscale_factor=1.0 field to distinguish from upscaled images. |
| 6b. Upscaled rasters | 200 | OHR-Bench test set OR RealDAE subset (NOT DIQA-5000 — in training). 2× and 4× bicubic upscaling (100 images × 2 factors). | resolution_quality_score (measured on ORIGINAL before upscaling) + upscale_factor field | mobilenetv4 + siglip2 | Labels derived from pre-upscale originals. Tests whether head correctly predicts quality of the underlying document, not the interpolated image. |

### OOD Acquisition Status

**Status**: ⏳ Not started (Phase 6, P0)

### OOD Leakage Risk

DIQA-5000 is in training. OHR-Bench test split must be withheld from training labels — only OHR-Bench test split is used for OOD-Resolution 6b. DocLayNet OOD images for 6a must use pages NOT overlapping with DocLayNet images used in any other training dataset (global split registry required, different pages required).

---

## Section 7 — Cross-Head Consistency

### Head Interactions

| Related Head | Relationship | Consistency Requirement |
| --- | --- | --- |
| SIG-G5-5 (resolution_quality_reg) | Shares exact same 30,000 image training dataset | Must use global split registry (SHA256-keyed). MNV4-H3 is the fast pre-correction gate (~3ms); SIG-G5-5 is the SigLIP validation head (~50ms) for cross-checking model drift. Both must use the same L2 label field. |
| MNV4-H1 (orientation) | Same model, different task | Resolution quality inference happens after orientation/skew correction in the pipeline — pipeline ordering must be respected. Training images should be orientation-corrected before resolution labeling. |
| MNV4-H2 (skew_reg) | Same model, different task | Same pipeline ordering dependency as MNV4-H1. Skew-distorted images have reduced effective resolution; labels should reflect the corrected document quality. |

### Split Leakage Risk

**Level**: MEDIUM

DIQA-5000 is fully in training. OHR-Bench test split withheld from training. DocLayNet OOD renders (6a) must use pages not appearing in any other training split. Global split registry (SHA256-keyed) required for all DocLayNet and RVL-CDIP derived images across all training datasets.

### Label Convention

`resolution_quality_score` uses a log-normalized scale: 0.0 = needs_major_upscale (very small char_height, document unreadable), ~0.4-0.5 = needs_light_upscale, ~0.6-0.7 = optimal (32-48px char_height range), 1.0 = high-resolution beyond optimal. This convention must be identical between MNV4-H3 and SIG-G5-5 — both heads read the same L2 field.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| H3-G01 | — | `resolution.resolution_quality_score` not populated in OHR-Bench L2 metadata | Labeling pipeline not yet run on OHR-Bench | Run `label_resolution_quality.py` + `integrate_resolution_quality.py` on OHR-Bench (8,500 images) on Vultr A100 VM (~11 min at 12.1 img/s) | 0.5 days |
| H3-G02 | — | Multi-DPI rendering pipeline for DocLayNet/RVL-CDIP not yet implemented | `prepare_multitask_datasets.py resolution` subcommand not yet created | Implement resolution subcommand: render source PDFs at 8 DPI tiers, run labeling pipeline, build manifest | 2-3 days |
| H3-G03 | — | RealDAE labeling not yet run | Labeling pipeline not applied to RealDAE (1,200 images) | Run labeling pipeline on RealDAE | 0.5 days |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| H3-G04 | V2 labeling strategy not yet implemented (target ~3-4px IQR vs V1 9.0px) | V2 plan documented but not built (Sauvola + projection profiles + DBSCAN) | Implement Phase A of V2 strategy (Sauvola binarization + morphological closing) | 1-2 days |
| H3-G05 | Born-digital low-DPI paradox not explicitly represented in training data | Multi-DPI rendering pipeline not yet built | Include born-digital low-DPI renders in training pipeline (6a OOD category also stresses this) | Part of H3-G02 |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| H3-G06 | CJK char_height calibration not validated (CJK chars naturally larger; score may overestimate quality) | Add CJK-stratified validation during resolution labeling; audit DIQA-5000 CJK subset |
| H3-G07 | Image-only pages (no text) fall back to DPI heuristic — fallback not yet documented | Define and document DPI-only fallback label formula for text-absent pages |

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
