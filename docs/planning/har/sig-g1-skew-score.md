# Head Adequacy Review: skew_score (SIG-G1-4)

> **Status**: 🔄 Scaffolded — Analysis Pending
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-22
> **HAR Index**: [HAR_MASTER_INDEX.md](../HAR_MASTER_INDEX.md)
> **Batch**: B — IQA
> **Adequacy**: ⏳ TBD

---

## Section 1 — Head Identity

| Field | Value |
| --- | --- |
| Head ID | SIG-G1-4 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | skew_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | VQualA ≥ 0.92 (SRCC with human MOS) |
| Primary L2 Field | `ml_image_quality.skew_score` (Phase 1) OR augmentation parameter (Phase 2) |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: Human MOS / VLM scores → L2 field; Phase 2: sin(\|skew_angle\|) normalized to [0,1] → L2 field |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.skew_score` (float 0-1; Phase 1) / sin(|skew_angle|) normalized to [0,1] (Phase 2)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 VLM labels

**Label Provenance**: Phase 1: tier_0_exact (human MOS) or tier_1_annotation (VLM); Phase 2: tier_0_exact (sin(|skew_angle_degrees| × π/180) is computed from recorded angle parameter)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/diqa-5000_audit.md for skew_score-specific defect codes; note classical skew detector had zero variance in pilot study)_

**CRITICAL DISTINCTION**: skew_score (this head) is a 0-1 severity metric (how badly the document is skewed as a quality problem). SIG-G3-2 (skew_reg) predicts the actual skew angle in degrees. These are fundamentally different targets using different L2 fields (`ml_image_quality.skew_score` vs `geometric.skew_angle_degrees`). These heads must not be confused during label assembly or model evaluation.

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | _(analysis required)_ | — | — | _(check audit)_ | — |
| OHR-Bench | 10,800 | _(analysis required)_ | — | — | — | — |

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are generated from augmentation parameters at creation time. The skew angle applied during generation is converted to a 0-1 severity score via sin(|angle|) normalization.

- **Target**: 100,000 synthetic images via Augraphy/augmentation pipeline
- **Label provenance**: tier_0_exact (skew angle is recorded at generation time; skew_score computed deterministically)
- **Normalization**: skew_score = 1.0 − sin(|skew_angle_degrees| × π/180); score of 1.0 = perfectly aligned (0°); score of 0.0 = 90° skew (worst case)
- **Note**: Phase 2 self-labeling for skew_score uses the same skew_angle values as the skew training dataset (MNV4-H2 / SIG-G3-2), but converts angle → severity score rather than using the raw angle. SHA256 dedup required to prevent cross-dataset contamination.
- **Pipeline status**: _(analysis required — check if Phase 2 pipeline script exists)_

### Usable Pool Summary

- **Phase 1 usable**: _(analysis required)_
- **Phase 1 target**: 16,300 images
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images
- **Combined gap**: 100,000 Phase 2 images

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: Tier 1 (max(10, 3%) per quality bucket) — VLM pilot complete for 200 images (overall_quality focus; skew severity scoring not yet validated separately)
- Phase 1 OHR-Bench: Tier 2 (max(15, 10%)) — VLM labeling not yet started
- Phase 2: No VLM sampling needed (sin(angle) computation is deterministic ground truth)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| IQA-KI-SKEW-CLASS | DIQA-5000 | `classical skew detector` | Classical skew detector had zero variance in VLM pilot — useless as cross-validation signal for skew_score | OPEN |
| _(analysis required — review diqa-5000_audit.md for additional codes)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch affects all G1 VLM labels | HIGH — VLM may penalize skew similarly to rotation, causing label noise |
| IQA-KI-SKEW-DIST | skew_score (severity) vs skew_reg (angle degrees) naming confusion risk | HIGH — must ensure L2 field assembly uses `ml_image_quality.skew_score`, NOT `geometric.skew_angle_degrees` |
| IQA-KI-SKEW-CLASS | Classical skew detector has zero variance — no cross-validation signal | MEDIUM — removes one validation signal |
| _(check audit for additional KI codes)_ | — | — |

### Remediation Path

_(analysis required after reviewing DIQA-5000 audit and OHR-Bench L2 population status)_

---

## Section 3 — Assembled Training Dataset Adequacy

**Assembly Status**: 🔄 Phase 1 partial (16,300 images); Phase 2 not started (0/100,000)

**Target Count**: 16,300 (Phase 1) + 100,000 (Phase 2 synthetic) = 116,300 total

**Current Count**: 16,300 Phase 1 available; Phase 2 pipeline not yet created

| Requirement | Target | Current | Gap |
| --- | --- | --- | --- |
| Phase 1 total images | 16,300 | 16,300 | ✅ Met |
| Phase 2 total images | 100,000 | 0 | ❌ Not started |
| Phase 1 label tier | ≥80% tier_1 | Mixed: MOS (human) + VLM pilot | ⚠️ VLM SRCC below target; rotation mismatch risk elevated for skew |
| Phase 2 label source | sin(\|skew_angle\|) from augmentation params | Not applicable (self-labeling, deterministic) | ✅ No L2 dependency |
| DIQA-5000 coverage | 5,500 images | 5,500 (5,499 labeled) | ✅ Met |
| OHR-Bench coverage | 10,800 images | 10,800 (split TBD) | ⚠️ Labels not yet populated |
| Skew severity range coverage | ≥4 severity buckets (0/mild/moderate/severe) | unknown | ⚠️ Requires analysis |

**Blockers**:

- VLM labeling SRCC for skew_score (as severity) not yet measured — rotation construct mismatch may be especially problematic here.
- Classical skew detector has zero variance — cannot serve as cross-validation.
- OHR-Bench L2 `ml_image_quality.skew_score` field not yet populated.
- Phase 2 Augraphy synthetic pipeline not yet created.
- Label convention for skew_score vs skew_reg must be documented and locked before assembly.

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` _(not yet implemented)_

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | HIGH — skew is the core degradation signal; must cover severity range from hairline to severe | ≥4 skew severity buckets (none/mild/moderate/severe) | unknown | TBD |
| capture_method | `capture_method.method` | HIGH — camera documents have page curl / perspective skew; scanner documents have feed slip skew | ≥3 capture methods represented | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs lose texture cues used for skew severity perception | ≥2 modes (color + grayscale; binarized as edge case) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — warped aged documents may exhibit non-linear skew that differs from synthetic linear skew | ≥2 age classes (modern + aged) | unknown | TBD |
| domain | `domain.level1` | MEDIUM — ruled-line documents (forms) provide strong skew cues; free-form handwriting does not | ≥5 domains | unknown | TBD |
| layout_type | `structure.layout_type` | MEDIUM — multi-column layouts change perception of skew severity | ≥3 types | unknown | TBD |
| script_code | `language.script_code` | MEDIUM — CJK baseline alignment cues differ from Latin; affects VLM score assignment | ≥3 script families | unknown | TBD |
| resolution | `resolution.category` | LOW — skew severity is largely resolution-independent | ≥3 resolution tiers | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Scanner feed slip (linear skew) | `quality.degradations` (skew subtype) | ⏳ | DIQA-5000 may cover; OHR-Bench coverage unknown |
| Camera capture tilt (perspective skew) | `capture_method.method` (camera_smartphone) | ⚠️ | Perspective skew differs from linear skew; Phase 2 must include perspective variant |
| Page curl (non-linear skew) | `physical_degradation.warping_type` | ⚠️ | Non-linear skew not well-represented by sin(angle) normalization; label may be approximate |
| Mixed orientation + skew (rotated AND skewed) | Both `geometric.orientation_class` and `ml_image_quality.skew_score` | ⚠️ | VLM pilot shows rotation causes label noise; compound case is especially risky |
| Near-zero skew (hairline tilt, ≤0.5°) | `quality.degradations` | ⏳ | Phase 1 pool may lack near-zero skew examples; model may predict too aggressively |
| Binarized skewed documents | `image_properties.color_mode` | ⚠️ | OOD-4d; binarized docs lose texture cues used for skew perception |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types) | 500 | ✅ Direct | Skew combined with blur, compression, and shadow — skew_score must be evaluated amid compound degradation where visual cues for skew are obscured |
| 4b. Watermarked documents | 100 | ⚠️ Indirect | Watermark texture does not directly affect skew severity perception; low relevance |
| 4c. Book gutter shadow | 100 | ⚠️ Indirect | Shadow gradient may obscure ruled-line cues used for skew detection; secondary effect |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | color_mode=binarized absent from Phase 1 training; binary images change the texture cues available for skew severity estimation |
| OOD-Mixed cascade | TBD | ⚠️ Indirect | Multi-distortion compounds including skew-inducing physical distortions |

**OOD Acquisition Status**: ⏳ Not started (Phase 4)

**Missing OOD Sub-sources**: Compound distortion labeling for skew_score (as severity) requires human annotation (classical Hough-based skew detector has zero variance — cannot be used for OOD ground truth).

**OOD Leakage Risk**: DIQA-5000 is in training. OOD-Degradation must use non-DIQA-5000 sources only. OHR-Bench test split must be withheld from Phase 1 training. Additionally, any Phase 2 synthetic images that share source documents with the skew training dataset (MNV4-H2 / SIG-G3-2, 90K images) must be SHA256-deduped.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench (16,300 images); Phase 2: synthetic augmentation

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| All other G1 heads (G1-1 to G1-3, G1-5 to G1-6) | DIQA-5000 + OHR-Bench | Multi-label independence required; labels must not be derived from each other | ✅ Each head's label is independently computed from MOS/VLM/augmentation params |
| SIG-G3-2 (skew_reg) | Different datasets (skew training dataset) | CRITICAL naming confusion: skew_score (G1-4) = quality severity 0-1; skew_reg (G3-2) = angle in degrees | ✅ Different L2 fields (`ml_image_quality.skew_score` vs `geometric.skew_angle_degrees`); documented distinction |
| MNV4-H2 (skew_reg) | Different datasets (skew training dataset) | Same critical naming distinction as SIG-G3-2 | ✅ Different models, different L2 fields; documented distinction |
| SIG-G1-6 (overall_quality) | Same dataset | overall_quality may use weighted average of other G1 scores including skew_score as cross-check | ⚠️ Risk of circular dependency if G1-6 labels derived from G1-1..G1-5 |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits well-defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against both the IQA Phase 2 pool and the skew training dataset (90K images).

**Label Convention**: skew_score is 0-1 where 1.0 = perfectly aligned (no skew), 0.0 = severely skewed. Phase 2 derivation: skew_score = 1.0 − sin(|skew_angle_degrees| × π/180). This convention is INVERSE of the skew_reg target (larger angle = more problematic). Must be documented prominently in assembly script comments and model card.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G1-4-G01 | — | OHR-Bench `ml_image_quality.skew_score` not populated in L2 metadata | L2 enrichment pipeline not yet run on OHR-Bench | Run VLM labeling pipeline on OHR-Bench; populate `ml_image_quality.skew_score` | _(analysis required)_ |
| G1-4-G02 | — | Phase 2 Augraphy synthetic pipeline not yet created | Script `prepare_multitask_datasets.py iqa` not implemented | Implement IQA sub-command; compute skew_score = 1.0 − sin(\|angle\|) and record at generation time | _(analysis required)_ |
| G1-4-G03 | — | skew_score vs skew_reg label convention not formally documented | Risk of confusion between this head and SIG-G3-2 / MNV4-H2 during data assembly | Write label convention spec; add assertions in assembly script to verify correct L2 field used | _(analysis required)_ |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G1-4-G04 | Skew-severity-specific VLM SRCC not measured | VLM pilot focused on overall_quality; rotation construct mismatch may inflate error for this head | Run targeted VLM validation on skew_score severity labels; test with rotated vs non-rotated images separately | _(analysis required)_ |
| G1-4-G05 | Page-curl (non-linear skew) not well-modeled by sin(angle) normalization | Phase 2 uses linear skew; curved distortion has different perceptual severity | Investigate whether page_curl from warping dataset can provide skew_score soft labels | _(analysis required)_ |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G1-4-G06 | Skew subtype labels (linear/perspective/page-curl) not captured | Add skew_subtype field to Phase 2 generation; use during OOD analysis |
| G1-4-G07 | Near-zero skew hairline coverage not validated | Stratify Phase 2 generation to include ≥20% images with |angle| < 0.5° |

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
