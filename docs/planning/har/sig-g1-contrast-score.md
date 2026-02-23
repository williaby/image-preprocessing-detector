# Head Adequacy Review: contrast_score (SIG-G1-3)

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
| Head ID | SIG-G1-3 |
| Model | SigLIP 2 NAFlex |
| Group | G1 — Image Quality Assessment |
| Head Name | contrast_score |
| Task Type | Regression (0-1 continuous score) |
| Output Format | Gaussian NLL head (mu, sigma_sq) |
| Priority | P0 |
| Performance Target | VQualA ≥ 0.92 (SRCC with human MOS) |
| Primary L2 Field | `ml_image_quality.contrast_score` (Phase 1) OR augmentation parameter (Phase 2) |
| Shared-Data Heads | All G1 heads share the same Phase 1 training dataset (DIQA-5000 + OHR-Bench) |
| Training Phase | Phase 1 (IQA Foundational — first phase trained) |
| Label Strategy | Phase 1: Human MOS / VLM scores → L2 field; Phase 2: CLAHE / brightness adjustment factor → L2 field |

---

## Section 2 — Source Dataset Pool Analysis

**Required L2 Field**: `ml_image_quality.contrast_score` (float 0-1; Phase 1) / CLAHE or brightness adjustment factor augmentation parameter (Phase 2)

**Confidence Threshold**: ≥ 0.7 (tier_1_annotation or better) for Phase 1 VLM labels

**Label Provenance**: Phase 1: tier_0_exact (human MOS) or tier_1_annotation (VLM); Phase 2: tier_0_exact (augmentation parameter is ground truth)

**Audit-Derived Defects**: _(analysis required — check docs/audit/audits/diqa-5000_audit.md for contrast_score-specific defect codes)_

### Phase 1 — Curated Source Pool

| Dataset | Total Images | Field Populated | Coverage % | Conf ≥ 0.7 | Audit Grade | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| DIQA-5000 | 5,500 | _(analysis required)_ | — | — | _(check audit)_ | — |
| OHR-Bench | 10,800 | _(analysis required)_ | — | — | — | — |

### Phase 2 — Synthetic Pipeline (Self-Labeling)

Phase 2 synthetic images do NOT require pre-populated L2 fields — labels are generated from augmentation parameters at creation time. The contrast_factor parameter applied during CLAHE or brightness adjustment in Augraphy generation is the ground-truth label, normalized to [0,1].

- **Target**: 100,000 synthetic images via Augraphy/augmentation pipeline
- **Label provenance**: tier_0_exact (CLAHE clip limit or brightness adjustment factor recorded at generation time)
- **Normalization**: contrast_score = clamp(contrast_factor / contrast_factor_max, 0, 1); low contrast_factor → low contrast_score
- **Pipeline status**: _(analysis required — check if Phase 2 pipeline script exists)_

### Usable Pool Summary

- **Phase 1 usable**: _(analysis required)_
- **Phase 1 target**: 16,300 images
- **Phase 2 usable**: 0 (pipeline not yet created)
- **Phase 2 target**: 100,000 images
- **Combined gap**: 100,000 Phase 2 images

### VLM Validation Sampling Tier

- Phase 1 DIQA-5000: Tier 1 (max(10, 3%) per quality bucket) — VLM pilot complete for 200 images (overall_quality focus; contrast-specific validation not yet run)
- Phase 1 OHR-Bench: Tier 2 (max(15, 10%)) — VLM labeling not yet started
- Phase 2: No VLM sampling needed (augmentation parameters are ground truth)

### Active Defects from Dataset Audits

| Defect ID | Source Dataset | Field | Description | Status |
| --- | --- | --- | --- | --- |
| _(analysis required — review diqa-5000_audit.md)_ | — | — | — | — |

### Known Issues Affecting This Head

| KI Code | Description | Impact |
| --- | --- | --- |
| IQA-KI-001 | VLM SRCC below target (0.53 non-rotated, 0.39 all) — rotation construct mismatch affects all G1 VLM labels | HIGH — contrast-specific VLM SRCC not yet measured separately |
| IQA-KI-CONTRAST | Watermarked documents (OOD-4b) may cause contrast scoring ambiguity — watermark reduces effective contrast | MEDIUM — overlap between watermark_severity and contrast_score signals |
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
| Phase 1 label tier | ≥80% tier_1 | Mixed: MOS (human) + VLM pilot | ⚠️ VLM SRCC below target |
| Phase 2 label source | Augmentation params (contrast factor) | Not applicable (self-labeling) | ✅ No L2 dependency |
| DIQA-5000 coverage | 5,500 images | 5,500 (5,499 labeled) | ✅ Met |
| OHR-Bench coverage | 10,800 images | 10,800 (split TBD) | ⚠️ Labels not yet populated |

**Blockers**:

- VLM labeling SRCC for contrast_score not yet measured independently (only overall_quality piloted).
- OHR-Bench L2 `ml_image_quality.contrast_score` field not yet populated in metadata_registry.
- Phase 2 Augraphy synthetic pipeline not yet created.

**Assembly Script**: `scripts/prepare_multitask_datasets.py iqa` _(not yet implemented)_

---

## Section 4 — 14-Dimension Diversity Assessment

**Overall Score**: _(TBD — computed after assembly)_

| Dimension | L2 Field | Relevance | Target | Current | Score |
| --- | --- | --- | --- | --- | --- |
| degradation | `quality.degradations` | HIGH — contrast reduction is the core degradation signal for this head | ≥4 contrast severity levels (high/adequate/low/very-low) | unknown | TBD |
| capture_method | `capture_method.method` | HIGH — scanner gamma curves, camera exposure, and born-digital rendering all produce different contrast distributions | ≥3 capture methods represented | unknown | TBD |
| color_mode | `image_properties.color_mode` | HIGH — binarized docs have maximum contrast (1-bit); grayscale and color differ in contrast perception | ≥2 modes (color + grayscale; binarized as special case) | unknown | TBD |
| document_age | `image_properties.document_age` | MEDIUM — aged documents exhibit faded ink and yellowed backgrounds that reduce effective contrast | ≥2 age classes (modern + aged) | unknown | TBD |
| domain | `domain.level1` | MEDIUM — financial documents have dense small text with high contrast requirements | ≥5 domains | unknown | TBD |
| resolution | `resolution.category` | MEDIUM — low-DPI images may appear low-contrast from anti-aliasing | ≥3 resolution tiers | unknown | TBD |
| script_code | `language.script_code` | MEDIUM — CJK ideographs have different stroke-to-background contrast than Latin | ≥3 script families | unknown | TBD |
| layout_type | `structure.layout_type` | LOW — layout type not a primary driver of contrast signal | ≥3 types | unknown | TBD |

---

## Section 5 — Wild Condition Coverage

**Overall Score**: _(TBD — computed after analysis)_

| Wild Condition | L2 Field Evidence | Status | Gap |
| --- | --- | --- | --- |
| Overexposed document (washed-out bright regions) | `quality.degradations` (contrast subtype) | ⏳ | Phase 1 pool may conflate low-contrast with overexposure; distinct degradation types |
| Underexposed document (dark/shadowed background) | `quality.degradations` (contrast subtype) | ⏳ | Book gutter shadow (OOD-4c) partially tests this; training may underrepresent |
| Watermark-reduced contrast | `physical_degradation.watermark_severity` | ⚠️ | OOD-4b tests watermarks; contrast_score and watermark_severity must be independently labeled |
| Faded ink (aged document) | `image_properties.document_age` | ⚠️ | DIQA-5000 may underrepresent historical document fading; separate from low-exposure |
| Colorful background reducing text contrast | `image_properties.colorful_background` | ⚠️ | Born-digital colorful-background docs reduce text legibility; must be in Phase 1 or Phase 2 |
| Binarized documents (contrast artificially maximized) | `image_properties.color_mode` | ⚠️ | OOD-4d tests binarized; model must correctly assign high contrast_score to 1-bit images |

---

## Section 6 — OOD Dataset Coverage

**Primary OOD Category**: OOD-Degradation (Phase 4, P0, 800 total images)

**IQA Head Sub-sources**: 4a multiply-distorted (500), 4b watermarked (100), 4c book gutter shadow (100), 4d binarized (100)

| OOD Sub-source | Images | Head-Relevant | Stress Scenario |
| --- | --- | --- | --- |
| 4a. Multiply-distorted (≥5 types) | 500 | ✅ Direct | Contrast reduction combined with blur, noise, and JPEG — contrast_score must be evaluated amid compound degradation |
| 4b. Watermarked documents | 100 | ✅ Direct | Watermarks directly reduce effective text-background contrast; primary test of contrast_score on overlaid content |
| 4c. Book gutter shadow | 100 | ✅ Direct | Shadow gradient creates spatially non-uniform contrast — primary relevance for contrast_score |
| 4d. Binarized (1-bit) docs | 100 | ✅ Direct | Binarized docs have maximum binary contrast; model must distinguish from real high-contrast |
| OOD-Mixed cascade | TBD | ⚠️ Indirect | Multi-distortion compounds that include contrast-reducing degradations |

**OOD Acquisition Status**: ⏳ Not started (Phase 4)

**Missing OOD Sub-sources**: Compound distortion labeling for contrast_score requires human annotation (classical histogram contrast detector has unknown SRCC — must be validated before use as OOD ground truth).

**OOD Leakage Risk**: DIQA-5000 is in training. OOD-Degradation must use non-DIQA-5000 sources only. OHR-Bench test split must be withheld from Phase 1 training.

---

## Section 7 — Cross-Head Consistency

**Shared Training Dataset**: Phase 1: DIQA-5000 + OHR-Bench (16,300 images); Phase 2: synthetic augmentation

**Shared Source Datasets**: All 6 G1 heads share the same image pool; labels are independent per head

| Related Head | Shared Data | Consistency Risk | Mitigation |
| --- | --- | --- | --- |
| All other G1 heads (G1-1, G1-2, G1-4 to G1-6) | DIQA-5000 + OHR-Bench | Multi-label independence required; labels must not be derived from each other | ✅ Each head's label is independently computed from MOS/VLM/augmentation params |
| SIG-G1-2 (noise_score) | Same dataset | Low contrast can increase apparent noise perception; risk of label correlation in low-contrast images | ⚠️ VLM prompt must score contrast and noise independently; separate scoring passes |
| SIG-G5-2 (shadow_reg) | Different datasets but OOD overlap | Book gutter shadow (OOD-4c) tests both contrast_score and shadow_reg; must be labeled independently | ✅ Different L2 fields; contrast_score is an IQA quality metric, shadow_reg is a physical severity score |
| SIG-G1-4 (skew_score) vs SIG-G3-2 (skew_reg) | Different datasets | Naming confusion risk: skew_score ≠ skew angle | ✅ Different L2 fields; documented distinction |
| SIG-G1-6 (overall_quality) | Same dataset | overall_quality may use weighted average of other G1 scores as cross-check | ⚠️ Risk of circular dependency if G1-6 labels derived from G1-1..G1-5 |

**Split Leakage Risk**: LOW (Phase 1) — DIQA-5000 and OHR-Bench test splits well-defined. MEDIUM (Phase 2) — synthetic images must be SHA256-deduped against all other training sets.

**Label Convention**: All G1 scores are 0-1 floats where 1.0 = perfect quality (optimal contrast), 0.0 = severe degradation (severe contrast loss). Binarized documents present a special case — binary contrast is maximum (1.0) but may not be perceptually optimal for all tasks. Label convention for binarized must be documented before training.

---

## Section 8 — Gap Registry & Remediation

### P0 Blockers (must resolve before assembly can run)

| Gap ID | Audit Defect | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- | --- |
| G1-3-G01 | — | OHR-Bench `ml_image_quality.contrast_score` not populated in L2 metadata | L2 enrichment pipeline not yet run on OHR-Bench | Run VLM labeling pipeline on OHR-Bench; populate `ml_image_quality.contrast_score` | _(analysis required)_ |
| G1-3-G02 | — | Phase 2 Augraphy synthetic pipeline not yet created | Script `prepare_multitask_datasets.py iqa` not implemented | Implement IQA sub-command; record contrast_factor per image at generation time | _(analysis required)_ |
| G1-3-G03 | — | Binarized document label convention undefined | 1-bit images have technically maximum contrast but may not represent "good" quality | Document and apply consistent label convention for binarized images before assembly | _(analysis required)_ |

### P1 Improvements (resolve before evaluation begins)

| Gap ID | Description | Root Cause | Remediation | Effort |
| --- | --- | --- | --- | --- |
| G1-3-G04 | Contrast-specific VLM SRCC not measured independently | VLM pilot focused on overall_quality only | Run targeted VLM validation on contrast_score labels; verify SRCC ≥ 0.65 | _(analysis required)_ |
| G1-3-G05 | Colorful background docs underrepresented in Phase 1 | DIQA-5000/OHR-Bench may not include high-chroma background documents | Ensure Phase 2 includes colorful background variants; verify with L2 colorful_background field | _(analysis required)_ |

### P2 Nice-to-Have

| Gap ID | Description | Remediation |
| --- | --- | --- |
| G1-3-G06 | Contrast subtype labels (overexposed/underexposed/low-gamma/watermark) not captured | Add contrast_subtype field to Phase 2 generation; use during OOD analysis |
| G1-3-G07 | Spatial non-uniformity of contrast not captured by global score | Source images with localized contrast variation; note limitation in model card |

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
